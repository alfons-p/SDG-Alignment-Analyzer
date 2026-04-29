#!/usr/bin/env python3
"""
Extract raw candidate sentences from a stratified sample of PDFs.

Samples 10% of PDFs from data/raw/ stratified by year and state, extracts all
candidate sentences (Phase 1 only: segmentation + cleaning filters), assigns
tiers based on spaCy validation, deduplicates via Jaccard similarity, and saves
to data/processed/raw_sentences_10percent.csv for downstream labeling.

Output CSV columns:
  - text: candidate sentence
  - source: PDF filename
  - year: report year
  - state: Australian state/territory
  - tier: A (likely ACTION), B (borderline), C (likely NEUTRAL)
  - relevance_score: spaCy confidence (0.0 if spaCy unavailable)
  - passes_spacy: whether spaCy validation passed
  - has_action_verb: whether an action verb was detected
"""

import argparse
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.text_processor import TextProcessor
from src.pdf_extractor import PDFExtractor
from src.enhanced_pdf_extractor import SentenceReconstructor


def discover_pdfs(data_dir: Path) -> list[dict]:
    """Find all PDFs organized by year/state and return metadata dicts."""
    pdfs = []
    for year_dir in sorted(data_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for state_dir in sorted(year_dir.iterdir()):
            if not state_dir.is_dir():
                continue
            state = state_dir.name
            for pdf_path in sorted(state_dir.glob("*.pdf")):
                pdfs.append({
                    "path": pdf_path,
                    "filename": pdf_path.name,
                    "year": year,
                    "state": state,
                })
    return pdfs


def stratified_sample(pdfs: list[dict], fraction: float = 0.10, seed: int = 42) -> list[dict]:
    """Sample a fraction of PDFs stratified by year and state."""
    rng = random.Random(seed)
    buckets = defaultdict(list)
    for pdf in pdfs:
        key = (pdf["year"], pdf["state"])
        buckets[key].append(pdf)

    sampled = []
    for key, bucket in sorted(buckets.items()):
        n = max(1, round(len(bucket) * fraction))
        sampled.extend(rng.sample(bucket, min(n, len(bucket))))

    return sampled


def extract_sentences_from_pdf(
    pdf_path: Path,
    text_processor: TextProcessor,
    reconstructor: SentenceReconstructor | None,
) -> list[str]:
    """Extract candidate sentences (Phase 1 only) from a single PDF."""
    extractor = PDFExtractor()
    result = extractor.extract_text_from_pdf(pdf_path)
    raw_text = result.get("text", "")
    if not raw_text:
        return []

    cleaned = text_processor.clean_text(raw_text)
    if reconstructor:
        cleaned = reconstructor.reconstruct(cleaned)

    return text_processor.extract_candidate_sentences(cleaned)


def assign_tier(
    text: str,
    text_processor: TextProcessor,
) -> tuple[str, float, bool, bool]:
    """
    Assign a tier based on spaCy validation results.

    Returns: (tier, relevance_score, passes_spacy, has_action_verb)

    Tier A: passes spaCy AND relevance_score >= 0.6 (likely ACTION)
    Tier B: passes Phase 1 but fails spaCy OR score 0.4-0.6 (borderline)
    Tier C: passes Phase 1 but score < 0.4 or no action verb (likely NEUTRAL)
    """
    if text_processor.nlp is None:
        return "C", 0.0, False, False

    validation = text_processor._validate_sentence_structure(text)
    score = validation.get("confidence", 0.0)
    passes_spacy = validation.get("is_valid_activity", False)
    has_action_verb = validation.get("has_action_verb", False)

    if passes_spacy and has_action_verb and score >= 0.6:
        tier = "A"
    elif score >= 0.4 or (passes_spacy and not has_action_verb):
        tier = "B"
    else:
        tier = "C"

    return tier, score, passes_spacy, has_action_verb


def jaccard_dedup(sentences: list[dict], threshold: float = 0.9) -> list[dict]:
    """Remove near-identical sentences based on Jaccard similarity of word sets.

    Uses word-count bucketing to avoid O(n^2) comparisons: only compares sentences
    with similar word counts (within 30% of each other), since Jaccard > 0.9
    requires roughly the same number of words.
    """
    if not sentences:
        return sentences

    # Pre-compute word sets and word counts
    entries = []
    for entry in sentences:
        words = set(entry["text"].lower().split())
        entries.append((entry, words, len(words)))

    # Sort by word count for bucketing
    entries.sort(key=lambda x: x[2])

    kept = []
    kept_entries = []  # (entry, words, wc) for kept sentences

    for entry, words, wc in entries:
        is_dup = False
        # Only compare against kept sentences with similar word count
        min_wc = wc * threshold  # if jaccard > 0.9, size ratio must be close
        max_wc = wc / threshold if wc > 0 else 0

        for prev_entry, prev_words, prev_wc in kept_entries:
            if prev_wc < min_wc:
                continue
            if prev_wc > max_wc:
                break  # sorted, so all remaining are too large

            intersection = len(words & prev_words)
            union = len(words | prev_words)
            if union > 0 and intersection / union > threshold:
                is_dup = True
                break

        if not is_dup:
            kept_entries.append((entry, words, wc))
            kept.append(entry)

    removed = len(sentences) - len(kept)
    if removed > 0:
        print(f"  Jaccard dedup: removed {removed} near-duplicates ({len(kept)} remaining)")

    return kept


def main():
    parser = argparse.ArgumentParser(
        description="Extract candidate sentences from a stratified sample of council PDFs."
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data/raw"),
        help="Directory containing year/state/PDF structure (default: data/raw)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/raw_sentences_10percent.csv"),
        help="Output CSV path (default: data/processed/raw_sentences_10percent.csv)",
    )
    parser.add_argument(
        "--fraction", type=float, default=0.10,
        help="Fraction of PDFs to sample per year/state stratum (default: 0.10)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    parser.add_argument(
        "--jaccard-threshold", type=float, default=0.9,
        help="Jaccard similarity threshold for dedup (default: 0.9)",
    )
    parser.add_argument(
        "--min-words", type=int, default=20,
        help="Minimum word count for candidate sentences (default: 20)",
    )
    parser.add_argument(
        "--max-words", type=int, default=500,
        help="Maximum word count for candidate sentences (default: 500)",
    )
    parser.add_argument(
        "--no-dedup", action="store_true",
        help="Skip Jaccard deduplication step",
    )
    args = parser.parse_args()

    # Discover PDFs
    print(f"Discovering PDFs in {args.data_dir}...")
    all_pdfs = discover_pdfs(args.data_dir)
    print(f"  Found {len(all_pdfs)} PDFs")
    if not all_pdfs:
        print("No PDFs found. Exiting.")
        sys.exit(1)

    # Stratified sample
    sampled = stratified_sample(all_pdfs, fraction=args.fraction, seed=args.seed)
    print(f"  Sampled {len(sampled)} PDFs ({args.fraction:.0%} per stratum, seed={args.seed})")

    # Initialize text processor
    print("Loading spaCy model...")
    text_processor = TextProcessor(
        min_activity_length=args.min_words,
        max_activity_length=args.max_words,
    )
    reconstructor = SentenceReconstructor(text_processor.nlp) if text_processor.nlp else None

    # Extract sentences
    all_entries = []
    tier_counts = {"A": 0, "B": 0, "C": 0}

    for i, pdf_info in enumerate(sampled, 1):
        pdf_path = pdf_info["path"]
        year = pdf_info["year"]
        state = pdf_info["state"]
        print(f"  [{i}/{len(sampled)}] {pdf_info['filename']}...", end=" ", flush=True)

        try:
            sentences = extract_sentences_from_pdf(pdf_path, text_processor, reconstructor)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        for sent in sentences:
            tier, score, passes_spacy, has_action_verb = assign_tier(sent, text_processor)
            tier_counts[tier] += 1
            all_entries.append({
                "text": sent,
                "source": pdf_info["filename"],
                "year": year,
                "state": state,
                "tier": tier,
                "relevance_score": round(score, 4),
                "passes_spacy": passes_spacy,
                "has_action_verb": has_action_verb,
            })

        print(f"{len(sentences)} candidates")

    print(f"\nTotal candidate sentences: {len(all_entries)}")
    print(f"  Tier A (likely ACTION): {tier_counts['A']}")
    print(f"  Tier B (borderline):    {tier_counts['B']}")
    print(f"  Tier C (likely NEUTRAL): {tier_counts['C']}")

    # Dedup
    if not args.no_dedup:
        print("\nRunning Jaccard deduplication...")
        all_entries = jaccard_dedup(all_entries, threshold=args.jaccard_threshold)
        # Recount tiers after dedup
        tier_counts = {"A": 0, "B": 0, "C": 0}
        for entry in all_entries:
            tier_counts[entry["tier"]] += 1
        print(f"After dedup: {len(all_entries)} sentences")
        print(f"  Tier A: {tier_counts['A']}, Tier B: {tier_counts['B']}, Tier C: {tier_counts['C']}")

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "text", "source", "year", "state", "tier",
        "relevance_score", "passes_spacy", "has_action_verb",
    ]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in all_entries:
            writer.writerow(entry)

    print(f"\nSaved {len(all_entries)} sentences to {args.output}")


if __name__ == "__main__":
    main()