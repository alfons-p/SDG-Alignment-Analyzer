#!/usr/bin/env python3
"""Analyze potential false positives in detail."""

import json
from pathlib import Path
from collections import Counter

def load_json(path):
    with open(path) as f:
        return json.load(f)

def analyze_false_positives():
    """Analyze false positives from the extraction results."""
    results_path = Path("test_multi_pdf_results.json")
    if not results_path.exists():
        print(f"File not found: {results_path}")
        return

    data = load_json(results_path)

    all_false_positives = []

    print("="*80)
    print("DETAILED ANALYSIS: Potential False Positives")
    print("="*80)

    for pdf_result in data:
        pdf_name = pdf_result['pdf']
        activities = pdf_result.get('new', [])

        for i, act in enumerate(activities):
            text = act.get('text', '')
            text_lower = text.lower()
            confidence = act.get('confidence', 0)

            # Skip if confidence < 0.7
            if confidence < 0.7:
                continue

            # Check categories of false positives
            category = None

            # Financial/structural patterns
            if any(p in text_lower for p in ['financial', 'audit', 'actuarial', 'statements', 'liabilities', 'assets']):
                category = 'financial_structural'
            elif any(p in text_lower for p in ['manager', 'officer', 'director', 'executive', 'ceo', 'chief']):
                category = 'personnel_org'

            if category:
                all_false_positives.append({
                    'pdf': pdf_name,
                    'index': i,
                    'category': category,
                    'confidence': confidence,
                    'text': text,
                    'word_count': act.get('word_count', 0),
                    'main_verb': act.get('main_verb', ''),
                    'has_action_verb': act.get('has_action_verb', False)
                })

    # Summary
    print(f"\nTotal potential false positives: {len(all_false_positives)}\n")

    # Count by category
    categories = Counter(fp['category'] for fp in all_false_positives)
    print("Breakdown by category:")
    print("-" * 50)
    for category, count in categories.most_common():
        pct = count / len(all_false_positives) * 100
        print(f"  {category}: {count} ({pct:.1f}%)")

    # Show examples by category
    print("\n" + "="*80)
    print("SAMPLES BY CATEGORY")
    print("="*80)

    for category in categories.keys():
        matches = [fp for fp in all_false_positives if fp['category'] == category][:5]
        if matches:
            print(f"\n📌 {category.upper().replace('_', ' ')} ({categories[category]} total)")
            print("-" * 60)
            for fp in matches:
                print(f"\nPDF: {fp['pdf']}")
                print(f"Conf: {fp['confidence']}, Words: {fp['word_count']}, Verb: '{fp['main_verb']}'")
                print(f"Has action verb: {fp['has_action_verb']}")
                print(f"Text: \"{fp['text'][:150]}...\"")

    # Manual review - show diverse examples
    print("\n" + "="*80)
    print("COMPLETE EXAMPLES FOR MANUAL REVIEW")
    print("="*80)

    # Get diverse examples
    diverse_examples = []
    seen_categories = set()
    for fp in all_false_positives:
        if fp['category'] not in seen_categories and len(diverse_examples) < 15:
            diverse_examples.append(fp)
            seen_categories.add(fp['category'])

    # Add a few more from each category
    for category in categories.keys():
        cat_examples = [fp for fp in all_false_positives if fp['category'] == category][:3]
        for ex in cat_examples:
            if ex not in diverse_examples:
                diverse_examples.append(ex)

    for i, fp in enumerate(diverse_examples[:20], 1):
        print(f"\n{i}. [{fp['category']}] Conf: {fp['confidence']:.2f}")
        print(f"   Source: {fp['pdf']}")
        print(f"   Main verb: '{fp['main_verb']}', Has action: {fp['has_action_verb']}")
        print(f"   Text: \"{fp['text']}\"")

    # Analysis of action verbs
    print("\n" + "="*80)
    print("ACTION VERB ANALYSIS")
    print("="*80)

    with_action = [fp for fp in all_false_positives if fp['has_action_verb']]
    without_action = [fp for fp in all_false_positives if not fp['has_action_verb']]

    print(f"\nActivities WITH action verbs: {len(with_action)} ({len(with_action)/len(all_false_positives)*100:.1f}%)")
    print(f"Activities WITHOUT action verbs: {len(without_action)} ({len(without_action)/len(all_false_positives)*100:.1f}%)")

    if with_action:
        print("\nExamples WITH action verbs (likely valid activities):")
        for fp in with_action[:5]:
            print(f"  - [{fp['main_verb']}] {fp['text'][:80]}...")

    if without_action:
        print("\nExamples WITHOUT action verbs (questionable):")
        for fp in without_action[:5]:
            print(f"  - [{fp['main_verb']}] {fp['text'][:80]}...")

if __name__ == "__main__":
    analyze_false_positives()
