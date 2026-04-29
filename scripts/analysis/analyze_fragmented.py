#!/usr/bin/env python3
"""Analyze fragmented activities in the new extraction."""

import json
from pathlib import Path

def load_json(path):
    with open(path) as f:
        return json.load(f)

def find_fragmented(activities):
    """Find activities with fragmented starts."""
    fragmented_patterns = [
        ('given ', 'starts with "given" - likely dependent clause'),
        ('used to ', 'starts with "used to" - likely middle of sentence'),
        ('and ', 'starts with "and" - conjunction joining fragments'),
        ('but ', 'starts with "but" - conjunction joining fragments'),
        ('or ', 'starts with "or" - conjunction joining fragments'),
        ('also ', 'starts with "also" - adverb from previous context'),
        ('therefore ', 'starts with "therefore" - conclusion from previous'),
        ('however ', 'starts with "however" - contrast from previous'),
        ('which ', 'starts with "which" - relative clause'),
        ('this ', 'starts with "this" - demonstrative needing antecedent'),
        ('these ', 'starts with "these" - demonstrative needing antecedent'),
        ('such ', 'starts with "such" - demonstrative needing antecedent'),
    ]

    fragmented = []
    for activity in activities:
        text = activity.get('text', '').lower()
        for pattern, reason in fragmented_patterns:
            if text.startswith(pattern):
                fragmented.append({
                    'activity': activity,
                    'pattern': pattern.strip(),
                    'reason': reason,
                    'word_count': activity.get('word_count', 0),
                    'text': activity.get('text', '')
                })
                break
    return fragmented

def main():
    # Load results
    results_path = Path("test_multi_pdf_results.json")
    if not results_path.exists():
        print(f"File not found: {results_path}")
        return

    data = load_json(results_path)

    print("="*80)
    print("FRAGMENTED ACTIVITY ANALYSIS")
    print("="*80)

    total_fragmented = 0
    total_activities = 0

    for pdf_result in data:
        pdf_name = pdf_result['pdf']
        new_activities = pdf_result.get('new', [])

        fragmented = find_fragmented(new_activities)
        total_fragmented += len(fragmented)
        total_activities += len(new_activities)

        if fragmented:
            print(f"\n{pdf_name}:")
            print(f"  Total activities: {len(new_activities)}")
            print(f"  Fragmented: {len(fragmented)} ({len(fragmented)/len(new_activities)*100:.1f}%)")

            for i, frag in enumerate(fragmented[:3], 1):  # Show first 3
                print(f"\n  Example {i}: {frag['reason']}")
                print(f"    Word count: {frag['word_count']}")
                print(f"    Text: \"{frag['text'][:150]}{'...' if len(frag['text']) > 150 else ''}\"")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total activities across all PDFs: {total_activities}")
    print(f"Total fragmented activities: {total_fragmented}")
    print(f"Percentage fragmented: {total_fragmented/total_activities*100:.2f}%")

    # Show all fragmented patterns found
    print(f"\nFragmented patterns found:")
    all_fragmented = []
    for pdf_result in data:
        all_fragmented.extend(find_fragmented(pdf_result.get('new', [])))

    from collections import Counter
    patterns = Counter(f['pattern'] for f in all_fragmented)
    for pattern, count in patterns.most_common():
        print(f"  '{pattern}': {count} instances")

if __name__ == "__main__":
    main()
