#!/usr/bin/env python3
"""Test activity extraction on multiple PDFs with side-by-side comparison."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.activity_extractor import ActivityExtractor

def find_existing_result(pdf_path):
    """Find existing result file for a PDF."""
    base_name = pdf_path.stem
    # Try various patterns
    patterns = [
        Path(f"results/by_council/{base_name}_alignment.json"),
        Path(f"results/by_council/{base_name.replace(' ', '_')}_alignment.json"),
    ]
    for pattern in patterns:
        if pattern.exists():
            return pattern
    return None

def extract_sample_activities(activities, n=3):
    """Extract sample activities of different lengths."""
    samples = {
        'short': [],
        'medium': [],
        'long': [],
        'with_bullets': [],
        'fragmented': []
    }

    for act in activities:
        text = act.get('text', '')
        wc = act.get('word_count', 0)

        # Categorize
        if 15 <= wc <= 25 and len(samples['short']) < n:
            samples['short'].append(act)
        elif 40 <= wc <= 60 and len(samples['medium']) < n:
            samples['medium'].append(act)
        elif wc >= 80 and len(samples['long']) < n:
            samples['long'].append(act)

        if '•' in text and len(samples['with_bullets']) < n:
            samples['with_bullets'].append(act)

        if text.startswith(('used to', 'given', 'and', 'or', 'but')) and len(samples['fragmented']) < n:
            samples['fragmented'].append(act)

    return samples

def test_pdf(pdf_path, extractor):
    """Test extraction on a single PDF."""
    print(f"\n{'='*80}")
    print(f"Testing: {pdf_path.name}")
    print(f"{'='*80}")

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return None

    # Load existing result
    existing_path = find_existing_result(pdf_path)
    existing_activities = []
    if existing_path:
        try:
            with open(existing_path) as f:
                existing_data = json.load(f)
                existing_activities = existing_data.get('activities', [])
            print(f"✓ Found existing result: {existing_path.name}")
        except Exception as e:
            print(f"⚠ Could not load existing result: {e}")

    # Run new extraction
    try:
        result = extractor.extract_from_pdf(pdf_path)
        new_activities = result.get('activities', [])
        print(f"✓ New extraction completed: {len(new_activities)} activities")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Compare statistics
    print(f"\n{'─'*80}")
    print("STATISTICS COMPARISON")
    print(f"{'─'*80}")

    if existing_activities:
        print(f"{'Metric':<30} {'Before':<15} {'After':<15} {'Change':<15}")
        print(f"{'─'*30} {'─'*15} {'─'*15} {'─'*15}")
        print(f"{'Total activities':<30} {len(existing_activities):<15} {len(new_activities):<15} {len(new_activities) - len(existing_activities):+15}")

        old_bullets = sum(1 for a in existing_activities if '•' in a.get('text', ''))
        new_bullets = sum(1 for a in new_activities if '•' in a.get('text', ''))
        print(f"{'With embedded bullets':<30} {old_bullets:<15} {new_bullets:<15} {new_bullets - old_bullets:+15}")

        old_long = sum(1 for a in existing_activities if a.get('word_count', 0) > 100)
        new_long = sum(1 for a in new_activities if a.get('word_count', 0) > 100)
        print(f"{'Activities >100 words':<30} {old_long:<15} {new_long:<15} {new_long - old_long:+15}")

        old_frag = sum(1 for a in existing_activities if a.get('text', '').startswith(('used to', 'given',)))
        new_frag = sum(1 for a in new_activities if a.get('text', '').startswith(('used to', 'given',)))
        print(f"{'Fragmented starts':<30} {old_frag:<15} {new_frag:<15} {new_frag - old_frag:+15}")

        old_avg = sum(a.get('word_count', 0) for a in existing_activities) / len(existing_activities) if existing_activities else 0
        new_avg = sum(a.get('word_count', 0) for a in new_activities) / len(new_activities) if new_activities else 0
        print(f"{'Avg words/activity':<30} {old_avg:<15.1f} {new_avg:<15.1f} {new_avg - old_avg:+15.1f}")

    # Extract and display side-by-side examples
    if existing_activities and new_activities:
        print(f"\n{'─'*80}")
        print("SIDE-BY-SIDE EXAMPLES")
        print(f"{'─'*80}")

        old_samples = extract_sample_activities(existing_activities, n=2)
        new_samples = extract_sample_activities(new_activities, n=2)

        # Example 1: Bullet point handling
        if old_samples['with_bullets']:
            print(f"\n📌 EXAMPLE 1: EMBEDDED BULLETS")
            print(f"{'─'*80}")
            old_text = old_samples['with_bullets'][0].get('text', '')
            print(f"BEFORE ({len(old_text.split())} words):")
            print(f"  \"{old_text[:200]}{'...' if len(old_text) > 200 else ''}\"")
            print(f"\nAFTER (properly split - see new activities):")
            if new_samples['medium']:
                new_text = new_samples['medium'][0].get('text', '')
                print(f"  \"{new_text[:200]}{'...' if len(new_text) > 200 else ''}\"")

        # Example 2: Long activity
        if old_samples['long']:
            print(f"\n📌 EXAMPLE 2: VERY LONG ACTIVITY")
            print(f"{'─'*80}")
            old_text = old_samples['long'][0].get('text', '')
            print(f"BEFORE ({len(old_text.split())} words):")
            print(f"  \"{old_text[:250]}{'...' if len(old_text) > 250 else ''}\"")
            print(f"\nAFTER (split into shorter activities):")
            if new_samples['short']:
                new_text = new_samples['short'][0].get('text', '')
                print(f"  \"{new_text[:200]}{'...' if len(new_text) > 200 else ''}\"")

        # Example 3: Fragmented start
        if old_samples['fragmented']:
            print(f"\n📌 EXAMPLE 3: FRAGMENTED ACTIVITY")
            print(f"{'─'*80}")
            old_text = old_samples['fragmented'][0].get('text', '')
            print(f"BEFORE ({len(old_text.split())} words):")
            print(f"  \"{old_text[:200]}{'...' if len(old_text) > 200 else ''}\"")
            print(f"\nAFTER (cleaner boundary):")
            if new_samples['medium'] and len(new_samples['medium']) > 1:
                new_text = new_samples['medium'][1].get('text', '')
                print(f"  \"{new_text[:200]}{'...' if len(new_text) > 200 else ''}\"")

    return {
        'pdf': pdf_path.name,
        'before_count': len(existing_activities) if existing_activities else 0,
        'after_count': len(new_activities),
        'existing': existing_activities,
        'new': new_activities
    }

def main():
    """Run tests on multiple PDFs."""
    # Test files to process
    test_pdfs = [
        Path("data/raw/2023/VIC/VIC_Alpine_Rural_2023.pdf"),
        Path("data/raw/2023/VIC/VIC_Ararat_Rural_2023.pdf"),
        Path("data/raw/2023/NSW/NSW_Ballina_Urban_2023.pdf"),
        Path("data/raw/2023/NSW/NSW_Balranald_Rural_2023.pdf"),
        Path("data/raw/2024/VIC/VIC_Bass Coast_Urban_2024.pdf"),
    ]

    # Create extractor
    extractor = ActivityExtractor(
        min_activity_length=15,
        max_activity_length=100
    )

    results = []

    print("="*80)
    print("ACTIVITY EXTRACTION COMPARISON TEST")
    print("Testing improved boundary detection across multiple PDFs")
    print("="*80)

    for pdf_path in test_pdfs:
        result = test_pdf(pdf_path, extractor)
        if result:
            results.append(result)

    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    print(f"{'PDF':<40} {'Before':<10} {'After':<10} {'Change':<10}")
    print(f"{'─'*40} {'─'*10} {'─'*10} {'─'*10}")
    for r in results:
        change = r['after_count'] - r['before_count']
        print(f"{r['pdf'][:39]:<40} {r['before_count']:<10} {r['after_count']:<10} {change:+10}")

    # Save detailed results
    output_path = Path("test_multi_pdf_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Detailed results saved to: {output_path}")

if __name__ == "__main__":
    main()
