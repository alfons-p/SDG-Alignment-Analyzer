#!/usr/bin/env python3
"""
Split labeled sentence data into train/val/test for activity classifier training.

Splits at the document level (all sentences from one PDF go to one split) to
prevent information leakage. Stratified by state to ensure geographic diversity.

Usage:
    python scripts/split_activity_data.py
    python scripts/split_activity_data.py --input data/processed/sentence_labels_raw_deepseek_deepseek-v3.2.csv
    python scripts/split_activity_data.py --ratios 50 25 25
"""

import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Split labeled sentence data into train/val/test for activity classifier."
    )
    parser.add_argument(
        "--input", type=Path,
        default=Path("data/processed/sentence_labels_raw_deepseek_deepseek-v3.2.csv"),
        help="Input CSV with LLM labels (default: deepseek-v3.2)",
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
    args = parser.parse_args()

    # Validate ratios
    if abs(sum(args.ratios) - 100) > 1:
        parser.error(f"Ratios must sum to 100, got {sum(args.ratios)}")
    train_pct, val_pct, _ = args.ratios

    # Load data, filter out errors
    rows = []
    error_count = 0
    with open(args.input, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["label"] in ("ERROR", "PARSE_ERROR"):
                error_count += 1
                continue
            rows.append(row)

    print(f"Loaded {len(rows)} valid rows (skipped {error_count} ERROR/PARSE_ERROR)")

    # Group by source document
    docs = defaultdict(list)
    for row in rows:
        docs[row["source"]].append(row)

    print(f"Unique documents: {len(docs)}")

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
    fieldnames = ["text", "source", "year", "state", "tier", "label", "reasoning", "model"]

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
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in split_rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

        print(f"\n{split_name}: {len(split_rows)} sentences from {len(split_docs)} docs")
        print(f"  Labels: {dict(label_counts)}")
        print(f"  States: {dict(state_counts)}")
        print(f"  Saved to {output_path}")


if __name__ == "__main__":
    main()