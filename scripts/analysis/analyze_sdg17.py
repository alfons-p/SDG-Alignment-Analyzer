#!/usr/bin/env python3
"""Detailed analysis of SDG 17 activities."""

import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

def load_alignment_results():
    """Load SDG alignment results."""
    results_path = Path("sdg_alignment_results.json")
    if not results_path.exists():
        print(f"Error: {results_path} not found")
        return []

    with open(results_path) as f:
        data = json.load(f)

    return data.get('results', [])


def create_csv(activities):
    """Create CSV file from alignment results."""
    csv_path = Path("sdg_alignment_results.csv")

    # Define CSV columns
    columns = [
        'activity_text',
        'source_pdf',
        'primary_sdg',
        'confidence',
        'word_count',
        'sdg_1_score',
        'sdg_2_score',
        'sdg_3_score',
        'sdg_4_score',
        'sdg_5_score',
        'sdg_6_score',
        'sdg_7_score',
        'sdg_8_score',
        'sdg_9_score',
        'sdg_10_score',
        'sdg_11_score',
        'sdg_12_score',
        'sdg_13_score',
        'sdg_14_score',
        'sdg_15_score',
        'sdg_16_score',
        'sdg_17_score',
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for result in activities:
            row = {
                'activity_text': result.get('activity', ''),
                'source_pdf': result.get('source_pdf', ''),
                'primary_sdg': result.get('primary_sdg', ''),
                'confidence': result.get('confidence', 0),
                'word_count': result.get('word_count', 0),
            }

            # Add SDG scores
            scores = result.get('scores', {})
            for sdg_num in range(1, 18):
                row[f'sdg_{sdg_num}_score'] = scores.get(sdg_num, 0)

            writer.writerow(row)

    print(f"✓ CSV created: {csv_path}")
    print(f"  Total rows: {len(activities)}")
    return csv_path

def analyze_sdg17():
    """Analyze all SDG 17 activities."""
    results = load_alignment_results()

    if not results:
        return

    # Filter SDG 17 activities
    sdg17_activities = [r for r in results if r.get('primary_sdg') == 17]

    print("="*80)
    print("SDG 17 ANALYSIS: Partnerships for the Goals")
    print("="*80)

    print(f"\nTotal activities classified as SDG 17: {len(sdg17_activities)}")

    if not sdg17_activities:
        print("\nNo activities classified as SDG 17.")
        return

    # Calculate statistics
    avg_confidence = sum(a.get('confidence', 0) for a in sdg17_activities) / len(sdg17_activities)
    print(f"Average confidence: {avg_confidence:.3f}")

    # Distribution by source PDF
    pdf_counts = Counter(a.get('source_pdf', '') for a in sdg17_activities)
    print("\nDistribution by source PDF:")
    for pdf, count in pdf_counts.most_common():
        print(f"  {pdf}: {count} activities")

    # Show all SDG 17 activities
    print("\n" + "-"*80)
    print("ALL SDG 17 ACTIVITIES (sorted by confidence)")
    print("-"*80)

    sorted_activities = sorted(sdg17_activities, key=lambda x: x.get('confidence', 0), reverse=True)

    for i, act in enumerate(sorted_activities, 1):
        print(f"\n{i}. Confidence: {act.get('confidence', 0):.3f}")
        print(f"   Source: {act.get('source_pdf', '')}")
        print(f"   Text: {act.get('activity', '')[:150]}...")

        # Show SDG 17 score vs other top scores
        scores = act.get('scores', {})
        if scores:
            top_3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"   Top 3 SDG scores: {', '.join([f'SDG {s[0]}: {s[1]:.3f}' for s in top_3])}")

    # Analysis of why these are SDG 17
    print("\n" + "="*80)
    print("ANALYSIS: Why are these activities classified as SDG 17?")
    print("="*80)

    print("""
SDG 17: Partnerships for the Goals - Strengthen the means of implementation and
revitalize the global partnership for sustainable development.

Key indicators in these activities:
- "In accordance with section..." (legal compliance/partnership with government)
- "Council adopted..." (policy implementation)
- "Agreement made under section..." (partnership agreements)
- "Council has prepared..." (reporting to higher authorities)
- "In accordance with the Act..." (regulatory compliance)

These activities represent:
1. Partnerships with state/federal government (compliance with Acts)
2. Policy implementation frameworks
3. Reporting mechanisms to higher authorities
4. Legal/regulatory compliance activities

This classification makes sense because:
- SDG 17 is about "means of implementation"
- Working "in accordance with" legislation represents partnership with government
- Reporting to higher authorities (state/federal) is a form of partnership
- Policy adoption aligns with implementation frameworks

However, many of these could ALSO be classified under other SDGs:
- SDG 16 (Governance) - for policy adoption and compliance
- Specific sector SDGs - depending on the actual content
""")

    # Cross-reference with other SDGs
    print("\n" + "-"*80)
    print("CROSS-REFERENCE: How do SDG 17 activities overlap with other SDGs?")
    print("-"*80)

    # Check second-highest scores for SDG 17 activities
    second_sdg_counts = Counter()
    for act in sdg17_activities:
        scores = act.get('scores', {})
        if scores:
            # Get second highest
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_scores) > 1:
                second_sdg = sorted_scores[1][0]
                second_sdg_counts[second_sdg] += 1

    print("\nSecond-highest SDG classifications for SDG 17 activities:")
    for sdg, count in second_sdg_counts.most_common():
        print(f"  SDG {sdg}: {count} activities ({count/len(sdg17_activities)*100:.1f}%)")

    return sdg17_activities


def main():
    """Main entry point."""
    print("Loading alignment results...")
    activities = load_alignment_results()

    if not activities:
        print("No activities found!")
        return

    print(f"Loaded {len(activities)} activities\n")

    # Create CSV
    csv_path = create_csv(activities)

    # Analyze SDG 17
    sdg17_activities = analyze_sdg17(activities)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total activities: {len(activities)}")
    print(f"CSV file: {csv_path}")
    print(f"SDG 17 activities: {len(sdg17_activities)}")


if __name__ == "__main__":
    main()
