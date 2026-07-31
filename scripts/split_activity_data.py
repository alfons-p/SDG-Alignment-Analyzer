#!/usr/bin/env python3
"""
Split labeled sentence data into train/val/test for activity classifier training.

Two modes:
  1. Single-model:  --input <csv>
  2. Multi-model consensus: --inputs <csv1> <csv2> <csv3> <csv4>

In consensus mode, merges all inputs on 'text' (inner join), computes:
  - consensus_label: "ACTION" if >=3 models say ACTION, "POLICY" if >=3 say POLICY,
                     else "NEUTRAL"
  - average_relevance_score: mean of relevance_score across all models

Splits at the document level (all sentences from one PDF go to one split) to
prevent information leakage. Stratified by state to ensure geographic diversity.

Usage:
    python scripts/split_activity_data.py
    python scripts/split_activity_data.py --input data/processed/sentence_labels_raw_deepseek_deepseek-v3.2.csv
    python scripts/split_activity_data.py --ratios 50 25 25
    python scripts/split_activity_data.py \\
        --inputs data/processed/sentence_labels_raw_deepseek-v4-pro-cloud-2026-05-03.csv \\
                 data/processed/sentence_labels_raw_glm-5.1-cloud-2026-05-03.csv \\
                 data/processed/sentence_labels_raw_kimi-k2.6-cloud-2026-05-03.csv \\
                 data/processed/sentence_labels_raw_minimax-m2.7-cloud-2026-05-03.csv
"""

import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path


def load_csv(path: Path):
    """Load a labeled CSV. Returns list of dict rows, skipping ERROR/PARSE_ERROR."""
    rows = []
    error_count = 0
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["label"] in ("ERROR", "PARSE_ERROR"):
                error_count += 1
                continue
            rows.append(row)
    if error_count:
        print(f"  {path.name}: {len(rows)} valid, {error_count} ERROR/PARSE_ERROR skipped")
    else:
        print(f"  {path.name}: {len(rows)} rows")
    return rows


def build_consensus(input_paths: list[Path]) -> list[dict]:
    """
    Merge multiple labeled CSVs on 'text', compute consensus label and avg relevance.

    Returns list of merged dicts with fields:
      text, source, year, state, tier, label, reasoning, model,
      relevance_score, passes_spacy, has_action_verb, consensus_label,
      average_relevance_score, model_votes
    """
    # Load all inputs, index by text
    text_entries: dict[str, list[dict]] = defaultdict(list)
    for path in input_paths:
        rows = load_csv(path)
        for row in rows:
            text_entries[row["text"]].append(row)

    n_models = len(input_paths)
    required = 3  # majority threshold

    merged = []
    only_in_some = 0
    for text, entries in text_entries.items():
        if len(entries) < n_models:
            only_in_some += 1
            continue

        # Count labels
        label_counts = Counter(e["label"] for e in entries)
        action_votes = label_counts.get("ACTION", 0)
        policy_votes = label_counts.get("POLICY", 0)

        if action_votes >= required:
            consensus = "ACTION"
        elif policy_votes >= required:
            consensus = "POLICY"
        else:
            consensus = "NEUTRAL"

        # Average relevance
        scores = [float(e.get("relevance_score", 0) or 0) for e in entries]
        avg_relevance = sum(scores) / len(scores)

        # Use first entry for metadata fields
        first = entries[0]
        merged.append({
            "text": text,
            "source": first["source"],
            "year": first["year"],
            "state": first["state"],
            "tier": first["tier"],
            "label": consensus,
            "reasoning": f"Consensus from {n_models} models: "
                         f"ACTION={action_votes} POLICY={policy_votes} "
                         f"NEUTRAL={label_counts.get('NEUTRAL', 0)}",
            "model": "consensus",
            "relevance_score": str(round(avg_relevance, 4)),
            "passes_spacy": first.get("passes_spacy", ""),
            "has_action_verb": first.get("has_action_verb", ""),
            "consensus_label": consensus,
            "average_relevance_score": str(round(avg_relevance, 4)),
            "model_votes": f"ACTION={action_votes}/POLICY={policy_votes}/"
                           f"NEUTRAL={label_counts.get('NEUTRAL', 0)}",
        })

    if only_in_some:
        print(f"  Dropped {only_in_some} texts not present in all {n_models} inputs")
    print(f"  Merged: {len(merged)} texts with consensus from {n_models} models")
    return merged


def main():
    parser = argparse.ArgumentParser(
        description="Split labeled sentence data into train/val/test for activity classifier."
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input", type=Path,
        default=None,
        help="Single input CSV with LLM labels",
    )
    input_group.add_argument(
        "--inputs", type=Path, nargs="+",
        default=None,
        help="Multiple input CSVs to merge via consensus (typically 4 models)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/splits"),
        help="Output directory for split files (default: data/splits)",
    )
    parser.add_argument(
        "--ratios", type=float, nargs=3, default=[50, 25, 25],
        help="Train/val/test split ratios as percentages (default: 50 25 25)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--save-merged", type=Path, default=None,
        help="Save merged consensus CSV to this path (only used with --inputs)",
    )
    args = parser.parse_args()

    # Determine which mode
    if args.inputs:
        print(f"Consensus mode: merging {len(args.inputs)} model outputs")
        rows = build_consensus(args.inputs)

        label_counts = Counter(r["label"] for r in rows)
        print(f"  Consensus labels: {dict(label_counts)}")

        # Save merged CSV if requested
        if args.save_merged:
            args.save_merged.parent.mkdir(parents=True, exist_ok=True)
            fieldnames = [
                "text", "source", "year", "state", "tier", "label", "reasoning",
                "model", "relevance_score", "passes_spacy", "has_action_verb",
                "consensus_label", "average_relevance_score", "model_votes",
            ]
            with open(args.save_merged, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            print(f"  Merged CSV saved to {args.save_merged}")
    elif args.input:
        print(f"Single-model mode: {args.input}")
        rows = load_csv(args.input)
    else:
        # Default single input
        default_path = Path("data/processed/sentence_labels_raw_deepseek_deepseek-v3.2.csv")
        print(f"Single-model mode (default): {default_path}")
        rows = load_csv(default_path)

    # Validate ratios
    if abs(sum(args.ratios) - 100) > 1:
        parser.error(f"Ratios must sum to 100, got {sum(args.ratios)}")
    train_pct, val_pct, _ = args.ratios

    # Group by source document
    docs = defaultdict(list)
    for row in rows:
        docs[row["source"]].append(row)

    print(f"\nUnique documents: {len(docs)}")

    # Show state distribution across docs
    doc_states = {}
    for source, doc_rows in docs.items():
        state = doc_rows[0]["state"]
        doc_states[source] = state

    state_counts = Counter(doc_states.values())
    print(f"Documents by state:")
    for state, count in sorted(state_counts.items()):
        print(f"  {state}: {count} docs")

    # Stratified split by state
    rng = random.Random(args.seed)

    # Group docs by state
    state_docs = defaultdict(list)
    for source, state in doc_states.items():
        state_docs[state].append(source)

    train_docs, val_docs, test_docs = [], [], []

    for state, sources in sorted(state_docs.items()):
        rng.shuffle(sources)
        n = len(sources)
        n_train = max(1, round(n * train_pct / 100))
        n_val = max(1, round(n * val_pct / 100))
        n_test = n - n_train - n_val
        if n_test < 1:
            n_test = 1
            n_train = n - n_val - n_test

        train_docs.extend(sources[:n_train])
        val_docs.extend(sources[n_train:n_train + n_val])
        test_docs.extend(sources[n_train + n_val:])

    print(f"\nSplit: {len(train_docs)} train / {len(val_docs)} val / {len(test_docs)} test docs")

    # Build split datasets
    fieldnames = [
        "text", "source", "year", "state", "tier", "label", "reasoning", "model",
        "relevance_score", "passes_spacy", "has_action_verb",
    ]
    if args.inputs:
        fieldnames.extend(["consensus_label", "average_relevance_score", "model_votes"])

    splits = {
        "train": train_docs,
        "val": val_docs,
        "test": test_docs,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split_docs in splits.items():
        split_rows = []
        for source in split_docs:
            split_rows.extend(docs[source])

        label_counts = Counter(r["label"] for r in split_rows)
        state_counts = Counter(r["state"] for r in split_rows)

        output_path = args.output_dir / f"activity_{split_name}.csv"
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in split_rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

        print(f"\n{split_name}: {len(split_rows)} sentences from {len(split_docs)} docs")
        print(f"  Labels: {dict(label_counts)}")
        print(f"  States: {dict(state_counts)}")
        print(f"  Saved to {output_path}")


if __name__ == "__main__":
    main()
