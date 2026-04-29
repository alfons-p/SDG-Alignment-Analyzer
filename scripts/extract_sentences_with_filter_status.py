#!/usr/bin/env python3
"""
Extract all raw sentences from a council annual report PDF and annotate each
with its filtering status across all the criteria used in activity extraction.

The output CSV has columns:
  - sentence_number: unique ID
  - word_count: word count of the raw sentence
  - reconstructed_word_count: word count after sentence reconstruction
  - text: raw sentence (as extracted from PDF)
  - reconstructed: sentence after reconstruction (fixes line breaks)
  - selected: whether it passed all filters (1) or not (0)
  - passes_length_check: word count within min/max bounds
  - passes_table_check: not flagged as table-like
  - passes_numbers_check: not mostly numbers
  - passes_meaningful_check: has meaningful content
  - passes_structural_check: not structural content (TOC, headers)
  - passes_fragmented_check: doesn't start with a fragment
  - passes_nonactivity_check: not non-activity content (financial, audit)
  - passes_spacy_validation: passes spaCy sentence structure validation
  - passes_action_verb_check: has a valid action verb
  - relevance_score: the computed relevance score (>0.90 required for selected)
"""

import csv
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.activity_extractor import ActivityExtractor
from src.text_processor import TextProcessor
from src.enhanced_pdf_extractor import SentenceReconstructor


def get_filter_status(text: str, reconstructed: str, text_processor: TextProcessor, min_words: int, max_words: int) -> dict:
    """
    Compute pass/fail for each filtering criterion on a single sentence.
    """
    raw_words = text.split()
    word_count = len(raw_words)
    recon_words = reconstructed.split()

    # 1. Length check
    passes_length = min_words <= word_count <= max_words

    # 2. Table check
    passes_table = not text_processor._looks_like_table(text)

    # 3. Numbers check
    passes_numbers = not text_processor._is_mostly_numbers(text)

    # 4. Meaningful content check
    passes_meaningful = text_processor._has_meaningful_content(text)

    # 5. Structural content check
    passes_structural = not text_processor._is_structural_content(text)

    # 6. Fragmented start check
    passes_fragmented = not text_processor._is_fragmented_start(text)

    # 7. Non-activity content check
    passes_nonactivity = not text_processor._is_non_activity_content(text)

    # 8. SpaCy validation (only if model loaded)
    if text_processor.nlp is not None:
        spacy_result = text_processor._validate_sentence_structure(text)
        passes_spacy = spacy_result['is_valid_activity']
        relevance_score = spacy_result['confidence']
        # Number ratio penalty (mirrors _score_activity)
        number_ratio = sum(1 for w in raw_words if any(c.isdigit() for c in w)) / word_count if word_count else 0
        if number_ratio > 0.3:
            relevance_score *= 0.5
        passes_action_verb = spacy_result.get('has_action_verb', False)
    else:
        passes_spacy = False
        passes_action_verb = False
        relevance_score = 0.0

    return {
        'passes_length_check': passes_length,
        'passes_table_check': passes_table,
        'passes_numbers_check': passes_numbers,
        'passes_meaningful_check': passes_meaningful,
        'passes_structural_check': passes_structural,
        'passes_fragmented_check': passes_fragmented,
        'passes_nonactivity_check': passes_nonactivity,
        'passes_spacy_validation': passes_spacy,
        'passes_action_verb_check': passes_action_verb,
        'relevance_score': relevance_score,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract sentences with filter status from a council annual report PDF.')
    parser.add_argument('pdf_path', help='Path to the council annual report PDF')
    parser.add_argument('--output', '-o', help='Output CSV path (default: results/raw_sentences_{council}_{year}.csv)')
    parser.add_argument('--min-words', type=int, default=20, help='Minimum word count (default: 20)')
    parser.add_argument('--max-words', type=int, default=500, help='Maximum word count (default: 500)')
    parser.add_argument('--spacy-model', default='en_core_web_sm', help='spaCy model name')
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)

    # Derive output path from PDF name
    if args.output:
        output_path = Path(args.output)
    else:
        stem = pdf_path.stem  # e.g. "NSW_Albury_Urban_2023"
        output_path = Path("results") / f"raw_sentences_{stem}.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading spaCy model: {args.spacy_model}...")
    text_processor = TextProcessor(
        min_activity_length=args.min_words,
        max_activity_length=args.max_words,
        spacy_model=args.spacy_model,
        unit="sentence"
    )

    # Build sentence reconstructor
    reconstructor = SentenceReconstructor(text_processor.nlp) if text_processor.nlp else None

    print(f"Extracting raw text from: {pdf_path}")
    from src.pdf_extractor import PDFExtractor
    extractor = PDFExtractor()
    raw_result = extractor.extract_text_from_pdf(pdf_path)
    raw_text = raw_result["text"]
    print(f"  Total raw characters: {len(raw_text):,}")

    # Segment into paragraphs and sentences (mirrors extract_activities logic)
    segments = text_processor.segment_into_paragraphs(raw_text)
    print(f"  Paragraphs: {len(segments)}")

    all_sentences = []  # list of dicts with filter status

    for seg_idx, segment in enumerate(segments):
        seg_word_count = len(segment.split())
        # Skip segments shorter than min_words (length pre-filter)
        if seg_word_count < args.min_words:
            continue

        sentences = text_processor.segment_into_sentences(segment, split_on_bullets=True)
        joined_groups = text_processor._smart_sentence_join(sentences)

        for group in joined_groups:
            group_words = group.split()
            group_word_count = len(group_words)

            if group_word_count < args.min_words:
                continue

            # Reconstruct this sentence (fixes line breaks)
            if reconstructor:
                reconstructed = reconstructor.reconstruct(group)
            else:
                reconstructed = group

            # The "raw" text we store is the pre-reconstruction group
            raw_sentence = group
            raw_word_count = group_word_count

            # If reconstructed is very different, use the original as "text" and
            # reconstructed as "reconstructed"
            text_for_filter = reconstructed if reconstructed.strip() else raw_sentence

            # Get all filter statuses
            filters = get_filter_status(
                text_for_filter,
                reconstructed,
                text_processor,
                args.min_words,
                args.max_words
            )

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

            all_sentences.append({
                'word_count': raw_word_count,
                'reconstructed_word_count': len(reconstructed.split()),
                'text': raw_sentence,
                'reconstructed': reconstructed,
                'selected': 1 if passes_all else 0,
                **filters
            })

    print(f"\nTotal sentences captured: {len(all_sentences)}")
    print(f"  Selected (pass all filters): {sum(1 for s in all_sentences if s['selected'])}")

    # Write CSV
    fieldnames = [
        'sentence_number', 'word_count', 'reconstructed_word_count',
        'text', 'reconstructed', 'selected',
        'passes_length_check', 'passes_table_check', 'passes_numbers_check',
        'passes_meaningful_check', 'passes_structural_check', 'passes_fragmented_check',
        'passes_nonactivity_check', 'passes_spacy_validation', 'passes_action_verb_check',
        'relevance_score'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, sent in enumerate(all_sentences, 1):
            row = {'sentence_number': i, **sent}
            writer.writerow(row)

    print(f"\nOutput written to: {output_path}")

    # Print filter breakdown
    print("\nFilter breakdown (sentences that FAIL each check):")
    n = len(all_sentences)
    if n == 0:
        print("  (no sentences)")
        return
    filters_to_show = [
        ('passes_length_check',         'length_check'),
        ('passes_table_check',         'table_check'),
        ('passes_numbers_check',       'numbers_check'),
        ('passes_meaningful_check',    'meaningful_check'),
        ('passes_structural_check',    'structural_check'),
        ('passes_fragmented_check',    'fragmented_check'),
        ('passes_nonactivity_check',   'nonactivity_check'),
        ('passes_spacy_validation',    'spacy_validation'),
        ('passes_action_verb_check',   'action_verb_check'),
        ('relevance_score <= 0.90',    'relevance_score'),
    ]
    for field, label in filters_to_show:
        if field == 'relevance_score <= 0.90':
            fails = sum(1 for s in all_sentences if s['relevance_score'] <= 0.90)
        else:
            fails = sum(1 for s in all_sentences if not s[field])
        print(f"  {label:25s}: {fails:5d} / {n}  ({fails/n*100:5.1f}%)")


if __name__ == '__main__':
    main()
