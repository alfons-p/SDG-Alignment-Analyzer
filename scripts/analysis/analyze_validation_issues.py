#!/usr/bin/env python3
"""Analyze activity validation issues."""

import json
from pathlib import Path
import re

def load_json(path):
    with open(path) as f:
        return json.load(f)

def analyze_validation_issues(activities, pdf_name):
    """Analyze validation issues in activities."""
    print(f"\n{'='*80}")
    print(f"VALIDATION ANALYSIS: {pdf_name}")
    print(f"{'='*80}")

    issues = {
        'high_confidence_non_activities': [],
        'weak_verbs_passed': [],
        'potential_false_positives': [],
        'questionable_activities': [],
        'rejected_patterns': []
    }

    # Keywords that suggest non-activities
    non_activity_indicators = [
        'financial statements', 'actuarial', 'accounting standards',
        'audited', 'audit', 'liabilities', 'accrued', 'funding position',
        'contributions are', 'statements have been prepared',
        'in accordance with', 'local government act',
        'local government', 'regulation', 'code of',
        'will jeremy', 'chief executive', 'officer',
        'organisational structure', 'director', 'manager',
        'executive', 'senior', 'officers reporting'
    ]

    # Weak action indicators
    weak_indicators = [
        'was', 'were', 'is', 'are', 'been', 'being',
        'had', 'has', 'have'
    ]

    for i, act in enumerate(activities):
        text = act.get('text', '')
        text_lower = text.lower()
        confidence = act.get('confidence', 0)
        has_action_verb = act.get('has_action_verb', False)
        word_count = act.get('word_count', 0)

        # Check for high confidence but non-activity content
        if confidence >= 0.8:
            for indicator in non_activity_indicators:
                if indicator in text_lower:
                    issues['high_confidence_non_activities'].append({
                        'index': i,
                        'text': text[:150],
                        'confidence': confidence,
                        'indicator': indicator,
                        'word_count': word_count
                    })
                    break

        # Check for weak verbs passing validation
        main_verb = act.get('main_verb', '')
        if main_verb in ['was', 'were', 'is', 'are', 'been', 'had', 'has']:
            if confidence >= 0.5:
                issues['weak_verbs_passed'].append({
                    'index': i,
                    'text': text[:150],
                    'main_verb': main_verb,
                    'confidence': confidence
                })

        # Check for potential false positives
        if confidence >= 0.7:
            # Financial/structural patterns
            if re.search(r'\b(actuarial|audit|financial statements?|liabilities|accrued|funding)\b', text_lower):
                issues['potential_false_positives'].append({
                    'index': i,
                    'text': text[:150],
                    'confidence': confidence,
                    'category': 'financial_structural'
                })

            # Personnel/organizational patterns
            if re.search(r'\b(chief executive|director|manager|officer|will jeremy|organisational structure)\b', text_lower):
                issues['potential_false_positives'].append({
                    'index': i,
                    'text': text[:150],
                    'confidence': confidence,
                    'category': 'personnel_org'
                })

            # Pure descriptive without clear action
            words = text_lower.split()
            if len(words) > 5:
                # Check if starts with "The" or "These" and is descriptive
                if words[0] in ['the', 'these', 'this'] and words[1] in ['is', 'are', 'was', 'were']:
                    issues['potential_false_positives'].append({
                        'index': i,
                        'text': text[:150],
                        'confidence': confidence,
                        'category': 'descriptive_only'
                    })

        # Questionable activities that shouldn't be activities
        if len(text) < 50 or text.count(' ') < 10:
            issues['questionable_activities'].append({
                'index': i,
                'text': text,
                'word_count': word_count
            })

    # Print findings
    print(f"\nTotal activities: {len(activities)}")

    if issues['high_confidence_non_activities']:
        print(f"\n⚠️  HIGH CONFIDENCE NON-ACTIVITIES ({len(issues['high_confidence_non_activities'])}):")
        for item in issues['high_confidence_non_activities'][:5]:
            print(f"\n  Item {item['index']} [conf: {item['confidence']}, {item['word_count']} words]:")
            print(f"  Indicator: '{item['indicator']}'")
            print(f"  Text: \"{item['text']}...\"")

    if issues['weak_verbs_passed']:
        print(f"\n⚠️  WEAK VERBS PASSING VALIDATION ({len(issues['weak_verbs_passed'])}):")
        for item in issues['weak_verbs_passed'][:5]:
            print(f"\n  Item {item['index']} [conf: {item['confidence']}]:")
            print(f"  Main verb: '{item['main_verb']}'")
            print(f"  Text: \"{item['text']}...\"")

    if issues['potential_false_positives']:
        print(f"\n⚠️  POTENTIAL FALSE POSITIVES ({len(issues['potential_false_positives'])}):")
        for item in issues['potential_false_positives'][:8]:
            print(f"\n  Item {item['index']} [conf: {item['confidence']}, cat: {item['category']}]:")
            print(f"  Text: \"{item['text']}...\"")

    if issues['questionable_activities']:
        print(f"\n⚠️  QUESTIONABLE ACTIVITIES (very short) ({len(issues['questionable_activities'])}):")
        for item in issues['questionable_activities'][:5]:
            print(f"\n  Item {item['index']} [{item['word_count']} words]:")
            print(f"  Text: \"{item['text']}\"")

    return issues

def main():
    results_path = Path("test_multi_pdf_results.json")
    if not results_path.exists():
        print(f"File not found: {results_path}")
        return

    data = load_json(results_path)

    all_issues = []
    for pdf_result in data:
        pdf_name = pdf_result['pdf']
        new_activities = pdf_result.get('new', [])

        issues = analyze_validation_issues(new_activities, pdf_name)
        all_issues.append({
            'pdf': pdf_name,
            'issues': issues,
            'total': len(new_activities)
        })

    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL VALIDATION SUMMARY")
    print(f"{'='*80}")

    total_high_conf_non_act = sum(len(a['issues']['high_confidence_non_activities']) for a in all_issues)
    total_weak_verbs = sum(len(a['issues']['weak_verbs_passed']) for a in all_issues)
    total_false_pos = sum(len(a['issues']['potential_false_positives']) for a in all_issues)
    total_questionable = sum(len(a['issues']['questionable_activities']) for a in all_issues)
    total_activities = sum(a['total'] for a in all_issues)

    print(f"\n{'Issue Type':<40} {'Count':<10} {'% of Total':<15}")
    print(f"{'─'*40} {'─'*10} {'─'*15}")
    print(f"{'High confidence non-activities':<40} {total_high_conf_non_act:<10} {total_high_conf_non_act/total_activities*100:.1f}%")
    print(f"{'Weak verbs passing validation':<40} {total_weak_verbs:<10} {total_weak_verbs/total_activities*100:.1f}%")
    print(f"{'Potential false positives':<40} {total_false_pos:<10} {total_false_pos/total_activities*100:.1f}%")
    print(f"{'Questionable (very short)':<40} {total_questionable:<10} {total_questionable/total_activities*100:.1f}%")
    print(f"{'─'*40} {'─'*10} {'─'*15}")
    print(f"{'TOTAL ACTIVITIES':<40} {total_activities:<10}")

if __name__ == "__main__":
    main()
