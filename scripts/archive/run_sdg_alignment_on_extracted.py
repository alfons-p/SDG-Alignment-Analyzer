#!/usr/bin/env python3
"""Run SDG alignment analysis on the 247 extracted activities."""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.alignment_engine import AlignmentEngine
from src.hybrid_alignment_engine import HybridAlignmentEngine
from src.config import SDG_DEFINITIONS


def load_extracted_activities():
    """Load activities from multi-PDF extraction results."""
    results_path = Path("test_multi_pdf_results.json")
    if not results_path.exists():
        print(f"Error: {results_path} not found. Run extraction first.")
        return []

    with open(results_path) as f:
        data = json.load(f)

    all_activities = []
    for pdf_result in data:
        pdf_name = pdf_result['pdf']
        activities = pdf_result.get('new', [])
        for act in activities:
            act['source_pdf'] = pdf_name
            all_activities.append(act)

    return all_activities


def run_sdg_alignment(activities, use_hybrid=True):
    """Run SDG alignment on activities."""
    print("="*80)
    print("SDG ALIGNMENT ANALYSIS")
    print("="*80)
    print(f"\nAnalyzing {len(activities)} activities...\n")

    # Initialize alignment engine
    if use_hybrid:
        print("Using Hybrid Alignment Engine (Sentence Transformer + sdgBERT)...")
        engine = HybridAlignmentEngine(
            ensemble_mode='weighted',
            sdg_bert_weight=0.55,
            st_weight=0.45
        )
    else:
        print("Using Standard Alignment Engine (Sentence Transformer)...")
        engine = AlignmentEngine()

    # Run alignment for each activity
    results = []
    sdg_scores = defaultdict(list)
    sdg_activities = defaultdict(list)

    for i, activity in enumerate(activities, 1):
        text = activity.get('text', '')
        if not text:
            continue

        # Get alignment scores
        try:
            alignment = engine.align_activity(text)
            # Extract scores from sdg_scores dict
            sdg_scores_dict = alignment.get('sdg_scores', {})

            # Find primary SDG (top_sdg from result)
            primary_sdg = alignment.get('top_sdg', 1)
            confidence = alignment.get('top_score', 0)

            # Convert scores dict to simple format
            scores = {sdg_num: data['score'] for sdg_num, data in sdg_scores_dict.items()}

            result = {
                'activity': text,
                'source_pdf': activity.get('source_pdf', ''),
                'primary_sdg': primary_sdg,
                'confidence': confidence,
                'scores': scores,
                'word_count': activity.get('word_count', 0)
            }
            results.append(result)

            # Track SDG distribution
            sdg_scores[primary_sdg].append(confidence)
            sdg_activities[primary_sdg].append({
                'text': text[:100],
                'confidence': confidence,
                'pdf': activity.get('source_pdf', '')
            })

            if i % 50 == 0:
                print(f"  Processed {i}/{len(activities)} activities...")

        except Exception as e:
            print(f"  Error processing activity {i}: {e}")
            continue

    return results, sdg_scores, sdg_activities


def analyze_results(results, sdg_scores, sdg_activities):
    """Analyze and print SDG alignment results."""
    print("\n" + "="*80)
    print("SDG ALIGNMENT RESULTS")
    print("="*80)

    # Overall statistics
    print(f"\nTotal activities analyzed: {len(results)}")
    avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0
    print(f"Average alignment confidence: {avg_confidence:.3f}")

    # SDG distribution
    print("\n" + "-"*60)
    print("SDG DISTRIBUTION")
    print("-"*60)

    # Sort by count
    sdg_counts = [(sdg, len(acts)) for sdg, acts in sdg_activities.items()]
    sdg_counts.sort(key=lambda x: x[1], reverse=True)

    print(f"{'SDG':<10} {'Count':<10} {'%':<8} {'Avg Conf':<10} {'Top Keyword':<30}")
    print("-"*60)

    for sdg, count in sdg_counts:
        scores = sdg_scores[sdg]
        avg_score = sum(scores) / len(scores) if scores else 0
        percentage = count / len(results) * 100

        # Get SDG definition
        sdg_def = SDG_DEFINITIONS.get(sdg, {})
        keywords = sdg_def.get('keywords', [])
        top_keyword = keywords[0] if keywords else 'N/A'

        print(f"{sdg:<10} {count:<10} {percentage:<8.1f} {avg_score:<10.3f} {top_keyword[:30]:<30}")

    # Top activities by SDG
    print("\n" + "-"*60)
    print("TOP ACTIVITIES BY SDG")
    print("-"*60)

    for sdg, count in sdg_counts[:5]:  # Top 5 SDGs
        print(f"\n📌 {sdg} ({count} activities)")
        acts = sorted(sdg_activities[sdg], key=lambda x: x['confidence'], reverse=True)[:3]
        for act in acts:
            print(f"  [conf: {act['confidence']:.3f}] {act['text'][:70]}...")

    # Activities with highest confidence
    print("\n" + "-"*60)
    print("HIGHEST CONFIDENCE ALIGNMENTS")
    print("-"*60)

    top_activities = sorted(results, key=lambda x: x['confidence'], reverse=True)[:10]
    for i, act in enumerate(top_activities, 1):
        sdg_def = SDG_DEFINITIONS.get(act['primary_sdg'], {})
        sdg_name = sdg_def.get('name', act['primary_sdg'])
        print(f"\n{i}. {act['primary_sdg']}: {sdg_name[:50]}")
        print(f"   Confidence: {act['confidence']:.3f}")
        print(f"   Activity: {act['activity'][:80]}...")

    # Save results
    output_path = Path("sdg_alignment_results.json")
    with open(output_path, 'w') as f:
        json.dump({
            'total_activities': len(results),
            'average_confidence': avg_confidence,
            'sdg_distribution': {sdg: len(acts) for sdg, acts in sdg_activities.items()},
            'results': results
        }, f, indent=2)

    print(f"\n✓ Results saved to: {output_path}")

    return results


def main():
    """Main entry point."""
    print("Loading extracted activities...")
    activities = load_extracted_activities()

    if not activities:
        print("No activities found!")
        return

    print(f"Loaded {len(activities)} activities\n")

    # Run alignment
    results, sdg_scores, sdg_activities = run_sdg_alignment(activities, use_hybrid=True)

    # Analyze results
    analyze_results(results, sdg_scores, sdg_activities)


if __name__ == "__main__":
    main()
