#!/usr/bin/env python3
"""Analyze the remaining high-confidence non-activities in detail."""

import json
from pathlib import Path
from collections import Counter

def load_json(path):
    with open(path) as f:
        return json.load(f)

def analyze_non_activities():
    """Analyze non-activities from the extraction results."""
    results_path = Path("test_multi_pdf_results.json")
    if not results_path.exists():
        print(f"File not found: {results_path}")
        return

    data = load_json(results_path)

    # Keywords/patterns that indicate non-activities
    non_activity_indicators = [
        ('code of', 'Code of Conduct/policy'),
        ('will jeremy', 'Personnel - CEO name'),
        ('senior', 'Personnel - senior staff'),
        ('officer', 'Personnel - officers'),
        ('manager', 'Personnel - managers'),
        ('executive', 'Personnel - executives'),
        ('audit', 'Audit text'),
        ('financial statements', 'Financial statements'),
        ('actuarial', 'Actuarial/financial'),
        ('in accordance with', 'Legal compliance text'),
        ('local government', 'Gov structure text'),
        ('local government act', 'Legislation reference'),
    ]

    all_matches = []

    print("="*80)
    print("DETAILED ANALYSIS: High Confidence Non-Activities")
    print("="*80)

    for pdf_result in data:
        pdf_name = pdf_result['pdf']
        activities = pdf_result.get('new', [])

        for i, act in enumerate(activities):
            text = act.get('text', '')
            text_lower = text.lower()
            confidence = act.get('confidence', 0)

            # Skip if confidence < 0.8
            if confidence < 0.8:
                continue

            # Check for non-activity indicators
            matched = False
            for indicator, category in non_activity_indicators:
                if indicator in text_lower:
                    all_matches.append({
                        'pdf': pdf_name,
                        'index': i,
                        'indicator': indicator,
                        'category': category,
                        'confidence': confidence,
                        'text': text,
                        'word_count': act.get('word_count', 0)
                    })
                    matched = True
                    break

    # Summary
    print(f"\nTotal high-confidence non-activities: {len(all_matches)}\n")

    # Count by category
    categories = Counter(m['category'] for m in all_matches)
    print("Breakdown by category:")
    print("-" * 50)
    for category, count in categories.most_common():
        print(f"  {category}: {count}")

    # Show examples by category
    print("\n" + "="*80)
    print("SAMPLE ACTIVITIES BY CATEGORY")
    print("="*80)

    for category in categories.keys():
        matches = [m for m in all_matches if m['category'] == category][:3]
        if matches:
            print(f"\n📌 {category.upper()} ({categories[category]} total)")
            print("-" * 60)
            for match in matches:
                print(f"\nPDF: {match['pdf']}")
                print(f"Conf: {match['confidence']}, Words: {match['word_count']}")
                print(f"Text: \"{match['text'][:120]}...\"")

    # Examine specific problematic patterns
    print("\n" + "="*80)
    print("PROBLEMATIC PATTERN ANALYSIS")
    print("="*80)

    # Group by indicator
    print("\nBreakdown by indicator keyword:")
    print("-" * 60)
    indicator_counts = Counter(m['indicator'] for m in all_matches)
    for indicator, count in indicator_counts.most_common():
        print(f"  '{indicator}': {count} instances")

    # Show a few complete examples for manual review
    print("\n" + "="*80)
    print("COMPLETE EXAMPLES FOR MANUAL REVIEW")
    print("="*80)

    # Pick diverse examples
    diverse_examples = []
    seen_categories = set()
    for match in all_matches:
        if match['category'] not in seen_categories and len(diverse_examples) < 10:
            diverse_examples.append(match)
            seen_categories.add(match['category'])

    for i, match in enumerate(diverse_examples, 1):
        print(f"\n{i}. [{match['category']}] Conf: {match['confidence']}")
        print(f"   Source: {match['pdf']}")
        print(f"   Text: \"{match['text']}\"")

if __name__ == "__main__":
    analyze_non_activities()
