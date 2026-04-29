#!/usr/bin/env python3
"""
Sample 30 random annual reports and produce per-PDF CSVs (like
extract_sentences_with_filter_status.py) plus an aggregated summary.

For each PDF the script saves:
  results/raw_sentences_{council}_{year}.csv

And prints a filter breakdown table. At the end it aggregates results
across all 30 PDFs into a single summary.
"""

import csv
import random
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.activity_extractor import ActivityExtractor
from src.text_processor import TextProcessor
from src.enhanced_pdf_extractor import SentenceReconstructor
from src.pdf_extractor import PDFExtractor


# ----------------------------------------------------------------------
# Filter-status computation (same logic as extract_sentences_with_filter_status.py)
# ----------------------------------------------------------------------
def get_filter_status(text: str, reconstructed: str, text_processor: TextProcessor,
                      min_words: int, max_words: int) -> dict:
    raw_words = text.split()
    word_count = len(raw_words)

    passes_length     = min_words <= word_count <= max_words
    passes_table      = not text_processor._looks_like_table(text)
    passes_numbers    = not text_processor._is_mostly_numbers(text)
    passes_meaningful = text_processor._has_meaningful_content(text)
    passes_structural = not text_processor._is_structural_content(text)
    passes_fragmented = not text_processor._is_fragmented_start(text)
    passes_nonactivity= not text_processor._is_non_activity_content(text)

    if text_processor.nlp is not None:
        spacy_result = text_processor._validate_sentence_structure(text)
        passes_spacy       = spacy_result['is_valid_activity']
        relevance_score    = spacy_result['confidence']
        number_ratio = (sum(1 for w in raw_words if any(c.isdigit() for c in w)) / word_count) if word_count else 0
        if number_ratio > 0.3:
            relevance_score *= 0.5
        passes_action_verb = spacy_result.get('has_action_verb', False)
    else:
        passes_spacy = passes_action_verb = False
        relevance_score = 0.0

    return {
        'passes_length_check':        passes_length,
        'passes_table_check':         passes_table,
        'passes_numbers_check':       passes_numbers,
        'passes_meaningful_check':    passes_meaningful,
        'passes_structural_check':    passes_structural,
        'passes_fragmented_check':    passes_fragmented,
        'passes_nonactivity_check':   passes_nonactivity,
        'passes_spacy_validation':    passes_spacy,
        'passes_action_verb_check':   passes_action_verb,
        'relevance_score':            relevance_score,
    }


# ----------------------------------------------------------------------
# Per-PDF extraction
# ----------------------------------------------------------------------
FIELDNAMES = [
    'sentence_number', 'word_count', 'reconstructed_word_count',
    'text', 'reconstructed', 'selected',
    'passes_length_check', 'passes_table_check', 'passes_numbers_check',
    'passes_meaningful_check', 'passes_structural_check', 'passes_fragmented_check',
    'passes_nonactivity_check', 'passes_spacy_validation', 'passes_action_verb_check',
    'relevance_score'
]


@dataclass
class PdfResult:
    pdf_path: Path
    council: str
    year: str
    sentences_total: int = 0
    sentences_selected: int = 0
    # per-filter fail counts
    fail_length: int = 0
    fail_table: int = 0
    fail_numbers: int = 0
    fail_meaningful: int = 0
    fail_structural: int = 0
    fail_fragmented: int = 0
    fail_nonactivity: int = 0
    fail_spacy: int = 0
    fail_action_verb: int = 0
    fail_relevance: int = 0
    error: str = ""


def extract_single_pdf(pdf_path: Path, text_processor: TextProcessor,
                       min_words: int, max_words: int) -> tuple[List[dict], PdfResult]:
    """Extract all sentences + filter status from one PDF. Returns (rows, stats)."""
    result = PdfResult(
        pdf_path=pdf_path,
        council="Unknown",
        year="Unknown"
    )

    # Parse council + year from filename
    stem = pdf_path.stem  # e.g. "NSW_Albury_Urban_2023"
    parts = stem.split("_")
    result.council = "_".join(parts[:-1]) if len(parts) > 1 else stem
    result.year = parts[-1] if parts[-1].isdigit() else "Unknown"

    try:
        extractor = PDFExtractor()
        raw_result = extractor.extract_text_from_pdf(pdf_path)
        raw_text = raw_result["text"]
    except Exception as e:
        result.error = str(e)
        return [], result

    reconstructor = (SentenceReconstructor(text_processor.nlp)
                     if text_processor.nlp else None)

    segments = text_processor.segment_into_paragraphs(raw_text)
    rows = []

    for segment in segments:
        seg_word_count = len(segment.split())
        if seg_word_count < min_words:
            continue

        sentences = text_processor.segment_into_sentences(segment, split_on_bullets=True)
        joined_groups = text_processor._smart_sentence_join(sentences)

        for group in joined_groups:
            group_word_count = len(group.split())
            if group_word_count < min_words:
                continue

            reconstructed = (reconstructor.reconstruct(group)
                            if reconstructor else group)

            text_for_filter = reconstructed.strip() if reconstructed.strip() else group
            filters = get_filter_status(text_for_filter, reconstructed,
                                        text_processor, min_words, max_words)

            passes_all = (
                filters['passes_length_check']
                and filters['passes_table_check']
                and filters['passes_numbers_check']
                and filters['passes_meaningful_check']
                and filters['passes_structural_check']
                and filters['passes_fragmented_check']
                and filters['passes_nonactivity_check']
                and filters['passes_spacy_validation']
                and filters['passes_action_verb_check']
                and filters['relevance_score'] > 0.90
            )

            n = group_word_count
            result.fail_length      += 0 if filters['passes_length_check']        else 1
            result.fail_table       += 0 if filters['passes_table_check']         else 1
            result.fail_numbers     += 0 if filters['passes_numbers_check']       else 1
            result.fail_meaningful  += 0 if filters['passes_meaningful_check']    else 1
            result.fail_structural  += 0 if filters['passes_structural_check']    else 1
            result.fail_fragmented  += 0 if filters['passes_fragmented_check']   else 1
            result.fail_nonactivity += 0 if filters['passes_nonactivity_check']   else 1
            result.fail_spacy       += 0 if filters['passes_spacy_validation']    else 1
            result.fail_action_verb += 0 if filters['passes_action_verb_check']   else 1
            result.fail_relevance  += 0 if filters['relevance_score'] > 0.90    else 1

            rows.append({
                'word_count': n,
                'reconstructed_word_count': len(reconstructed.split()),
                'text': group,
                'reconstructed': reconstructed,
                'selected': 1 if passes_all else 0,
                **filters
            })

    result.sentences_total    = len(rows)
    result.sentences_selected = sum(1 for r in rows if r['selected'])
    return rows, result


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Sample N random annual reports and produce per-PDF CSVs with filter status.')
    parser.add_argument('--data-dir', '-d', type=Path, default=Path('data/LGAcleannames'),
                        help='Root directory containing PDF subdirectories (default: data/LGAcleannames)')
    parser.add_argument('--n', '-n', type=int, default=30,
                        help='Number of random PDFs to sample (default: 30)')
    parser.add_argument('--seed', '-s', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--min-words', type=int, default=20)
    parser.add_argument('--max-words', type=int, default=500)
    parser.add_argument('--spacy-model', default='en_core_web_sm')
    parser.add_argument('--output-dir', type=Path, default=Path('results/raw_sentences_batch'),
                        help='Directory for per-PDF CSVs (default: results/raw_sentences_batch)')
    parser.add_argument('--summary-csv', type=Path, default=Path('results/raw_sentences_batch_summary.csv'),
                        help='Aggregated summary CSV path')
    args = parser.parse_args()

    random.seed(args.seed)

    # Collect all PDFs
    all_pdfs = sorted(args.data_dir.rglob("*.pdf"))
    print(f"Found {len(all_pdfs)} PDFs in {args.data_dir}")

    if len(all_pdfs) < args.n:
        print(f"WARNING: only {len(all_pdfs)} PDFs found, sampling all of them")
        sampled = all_pdfs
    else:
        sampled = random.sample(all_pdfs, args.n)
    print(f"Sampled {len(sampled)} PDFs:\n")

    # Initialize text processor once
    print(f"Loading spaCy model: {args.spacy_model}...")
    tp = TextProcessor(
        min_activity_length=args.min_words,
        max_activity_length=args.max_words,
        spacy_model=args.spacy_model,
        unit="sentence"
    )
    print("spaCy model loaded.\n")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_results: List[PdfResult] = []
    start_time = time.time()

    for i, pdf_path in enumerate(sampled, 1):
        rel = pdf_path.relative_to(args.data_dir)
        print(f"[{i:2d}/{len(sampled)}] {rel}...", end=" ", flush=True)

        rows, res = extract_single_pdf(pdf_path, tp, args.min_words, args.max_words)

        if res.error:
            print(f"ERROR: {res.error}")
        else:
            # Write per-PDF CSV
            csv_name = f"raw_sentences_{res.council}_{res.year}.csv"
            csv_path = args.output_dir / csv_name
            # Avoid collisions
            if csv_path.exists():
                csv_path = args.output_dir / f"raw_sentences_{res.council}_{res.year}_{i}.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
                for j, row in enumerate(rows, 1):
                    writer.writerow({'sentence_number': j, **row})

            print(f"{res.sentences_total} sentences, {res.sentences_selected} selected")

        all_results.append(res)

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.1f}s")

    # ------------------------------------------------------------------
    # Per-filter aggregated table
    # ------------------------------------------------------------------
    n_total = sum(r.sentences_total for r in all_results if not r.error)
    n_sel   = sum(r.sentences_selected for r in all_results if not r.error)
    n_pdfs  = sum(1 for r in all_results if not r.error)

    print(f"\n{'='*70}")
    print(f"AGGREGATED RESULTS ({n_pdfs} PDFs, {n_total} total sentences, {n_sel} selected)")
    print(f"{'='*70}")

    filters = [
        ('fail_length',      'length_check'),
        ('fail_table',       'table_check'),
        ('fail_numbers',     'numbers_check'),
        ('fail_meaningful',  'meaningful_check'),
        ('fail_structural',  'structural_check'),
        ('fail_fragmented',  'fragmented_check'),
        ('fail_nonactivity', 'nonactivity_check'),
        ('fail_spacy',       'spacy_validation'),
        ('fail_action_verb', 'action_verb_check'),
        ('fail_relevance',   'relevance_score'),
    ]

    print(f"\n{'Filter':<28} {'Fails':>8} {'Total':>8} {'Fail %':>8}")
    print("-" * 56)
    for attr, label in filters:
        fails = sum(getattr(r, attr, 0) for r in all_results if not r.error)
        print(f"  {label:<26} {fails:>8,} {n_total:>8,} {fails/max(n_total,1)*100:>7.1f}%")

    # ------------------------------------------------------------------
    # Per-PDF breakdown table
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print(f"PER-PDF SUMMARY")
    print(f"{'='*70}")
    print(f"\n{'PDF':<45} {'Total':>6} {'Sel':>5} {'LenFail':>7} {'TblFail':>7} "
          f"{'NumFail':>7} {'MeanFail':>8} {'StrFail':>7} {'FragFail':>9} "
          f"{'NonActFail':>10} {'SpacyFail':>10} {'VerbFail':>8} {'RelFail':>7}")
    print("-" * 160)

    for r in all_results:
        label = f"{r.council} ({r.year})"
        if r.error:
            print(f"  {label:<43}  ERROR: {r.error[:40]}")
            continue
        t = r.sentences_total
        s = r.sentences_selected
        print(f"  {label:<43} {t:>6} {s:>5} "
              f"{r.fail_length:>7} {r.fail_table:>7} {r.fail_numbers:>7} "
              f"{r.fail_meaningful:>8} {r.fail_structural:>7} {r.fail_fragmented:>9} "
              f"{r.fail_nonactivity:>10} {r.fail_spacy:>10} {r.fail_action_verb:>8} "
              f"{r.fail_relevance:>7}")

    # ------------------------------------------------------------------
    # Save summary CSV
    # ------------------------------------------------------------------
    summary_fields = [
        'pdf_path', 'council', 'year', 'sentences_total', 'sentences_selected',
        'fail_length', 'fail_table', 'fail_numbers', 'fail_meaningful',
        'fail_structural', 'fail_fragmented', 'fail_nonactivity',
        'fail_spacy', 'fail_action_verb', 'fail_relevance', 'error'
    ]
    with open(args.summary_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for r in all_results:
            writer.writerow({
                'pdf_path': str(r.pdf_path),
                'council': r.council,
                'year': r.year,
                'sentences_total': r.sentences_total,
                'sentences_selected': r.sentences_selected,
                'fail_length': r.fail_length,
                'fail_table': r.fail_table,
                'fail_numbers': r.fail_numbers,
                'fail_meaningful': r.fail_meaningful,
                'fail_structural': r.fail_structural,
                'fail_fragmented': r.fail_fragmented,
                'fail_nonactivity': r.fail_nonactivity,
                'fail_spacy': r.fail_spacy,
                'fail_action_verb': r.fail_action_verb,
                'fail_relevance': r.fail_relevance,
                'error': r.error,
            })
    print(f"\nSummary CSV saved to: {args.summary_csv}")


if __name__ == '__main__':
    main()
