#!/usr/bin/env python3
"""
Quality check for activity extraction with improved filters.

Randomly selects 20 annual reports, extracts activities, and samples 5%
for quality rating on:
1. Is it an activity text? (0-1 confidence)
2. Is it a city council government activity? (0-1 confidence)
"""

import random
import json
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.activity_extractor import ActivityExtractor


def get_random_pdfs(data_dir: Path, n: int = 20, seed: int = 42) -> List[Path]:
    """Get n random PDFs from data directory."""
    random.seed(seed)
    all_pdfs = list(data_dir.rglob("*.pdf"))
    selected = random.sample(all_pdfs, min(n, len(all_pdfs)))
    return selected


def extract_activities(pdf_path: Path) -> List[Dict]:
    """Extract activities from a PDF file using improved filters."""
    extractor = ActivityExtractor(
        min_activity_length=5,
        max_activity_length=150,
        use_llm_labeling=False,
        use_sentence_reconstruction=True,
        spacy_model="en_core_web_sm"
    )
    result = extractor.extract_from_pdf(pdf_path)
    return result.get("activities", [])


def sample_activities(activities: List[Dict], sample_rate: float = 0.05, seed: int = 42) -> List[Dict]:
    """Sample a percentage of activities."""
    random.seed(seed)
    n_samples = max(1, int(len(activities) * sample_rate))
    if len(activities) <= n_samples:
        return activities
    return random.sample(activities, n_samples)


def rate_activity(text: str) -> Tuple[float, float, str, str]:
    """
    Rate an activity text on two criteria.

    Returns:
        Tuple of (is_activity_score, is_council_score, activity_reason, council_reason)
    """
    text_lower = text.lower()

    # === IS IT AN ACTIVITY TEXT? ===

    # Strong activity indicators
    action_verbs_past = [
        'completed', 'implemented', 'delivered', 'constructed', 'built',
        'established', 'created', 'launched', 'initiated', 'introduced',
        'developed', 'installed', 'upgraded', 'renewed', 'refurbished',
        'purchased', 'acquired', 'commissioned', 'opened', 'started',
        'appointed', 'awarded', 'granted', 'funded', 'hosted', 'held',
        'conducted', 'undertook', 'achieved', 'performed', 'provided'
    ]

    action_verbs_present = [
        'implements', 'delivers', 'provides', 'supports', 'offers',
        'operates', 'manages', 'coordinates', 'facilitates', 'runs'
    ]

    # Non-activity indicators
    financial_patterns = [
        'fair value', 'carrying value', 'impairment', 'depreciation',
        'balance date', 'financial statements', 'recoverable amount',
        'valuation inputs', 'asset class', 'material impact'
    ]

    policy_patterns = [
        'action plan', 'priority area', 'key deliverable', 'strategic objective',
        'will be', 'will continue', 'to be', 'planned to', 'scheduled to'
    ]

    # Check for activity
    has_past_action = any(verb in text_lower for verb in action_verbs_past)
    has_present_action = any(verb in text_lower for verb in action_verbs_present)
    has_financial = any(pattern in text_lower for pattern in financial_patterns)
    has_policy = any(pattern in text_lower for pattern in policy_patterns)
    has_council = any(word in text_lower for word in ['council', 'shire', 'city', 'municipality', 'we ', 'our '])

    # Activity scoring
    if has_financial:
        is_activity = 0.2
        activity_reason = "Financial/accounting text"
    elif has_policy and not has_past_action:
        is_activity = 0.3
        activity_reason = "Policy/plan text or future action"
    elif has_past_action and has_council:
        is_activity = 0.95
        activity_reason = "Clear completed action with council subject"
    elif has_past_action:
        is_activity = 0.85
        activity_reason = "Completed action"
    elif has_present_action and has_council:
        is_activity = 0.80
        activity_reason = "Ongoing action with council subject"
    elif has_present_action:
        is_activity = 0.70
        activity_reason = "Ongoing action"
    elif has_council:
        is_activity = 0.50
        activity_reason = "Council-related but no clear action"
    else:
        is_activity = 0.30
        activity_reason = "No clear activity indicators"

    # === IS IT A COUNCIL ACTIVITY? ===

    council_services = [
        'library', 'child care', 'aged care', 'meals on wheels', 'waste',
        'recycling', 'road', 'footpath', 'drainage', 'park', 'reserve',
        'community centre', 'hall', 'swimming pool', 'sport', 'recreation',
        'planning permit', 'parking', 'ranger', 'animal', 'health inspection'
    ]

    non_council = ['nbn', 'telstra', 'state government', 'federal', 'commonwealth']

    has_council_service = any(service in text_lower for service in council_services)
    has_non_council = any(word in text_lower for word in non_council)

    if has_council and has_council_service:
        is_council = 0.95
        council_reason = "Explicit council with council service"
    elif has_council:
        is_council = 0.85
        council_reason = "Explicit council mention"
    elif has_council_service and not has_non_council:
        is_council = 0.70
        council_reason = "Council service without explicit council"
    elif has_non_council:
        is_council = 0.40
        council_reason = "May be non-council entity"
    else:
        is_council = 0.50
        council_reason = "Unclear if council activity"

    return is_activity, is_council, activity_reason, council_reason


def main():
    """Run quality check with improved extraction."""
    data_dir = Path("data/LGAcleannames")

    # Select 20 random PDFs
    print("=" * 80)
    print("ACTIVITY EXTRACTION QUALITY CHECK (IMPROVED FILTERS)")
    print("=" * 80)
    print("\nSelecting 20 random PDFs...")

    pdfs = get_random_pdfs(data_dir, n=20)

    print(f"\nSelected PDFs:")
    for i, pdf in enumerate(pdfs, 1):
        print(f"  {i:2d}. {pdf.relative_to(data_dir)}")

    # Extract activities from each PDF and sample 5%
    all_samples = []
    extraction_stats = []

    for pdf_path in pdfs:
        print(f"\n{'='*80}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*80}")

        try:
            activities = extract_activities(pdf_path)
            total_extracted = len(activities)
            print(f"Total activities extracted: {total_extracted}")

            # Sample 5%
            samples = sample_activities(activities, sample_rate=0.05)
            print(f"Sample size (5%): {len(samples)}")

            extraction_stats.append({
                'source': pdf_path.name,
                'total_extracted': total_extracted,
                'sample_size': len(samples)
            })

            for i, activity in enumerate(samples, 1):
                text = activity.get("text", "")
                is_activity, is_council, act_reason, council_reason = rate_activity(text)

                all_samples.append({
                    "source": pdf_path.name,
                    "activity_num": i,
                    "total_in_sample": len(samples),
                    "text": text,
                    "text_length": len(text),
                    "word_count": len(text.split()),
                    "is_activity_score": is_activity,
                    "is_council_score": is_council,
                    "activity_reason": act_reason,
                    "council_reason": council_reason,
                    "avg_confidence": (is_activity + is_council) / 2,
                    "confidence": activity.get("confidence", "N/A")
                })

        except Exception as e:
            print(f"ERROR processing {pdf_path.name}: {e}")
            continue

    # Calculate statistics
    print(f"\n{'='*80}")
    print("QUALITY STATISTICS")
    print(f"{'='*80}")

    total_samples = len(all_samples)
    if total_samples == 0:
        print("No samples extracted!")
        return

    activity_scores = [s['is_activity_score'] for s in all_samples]
    council_scores = [s['is_council_score'] for s in all_samples]

    print(f"\nTotal samples: {total_samples}")
    print(f"\nIS ACTIVITY TEXT (0-1):")
    print(f"  Mean: {sum(activity_scores)/total_samples:.3f}")
    print(f"  Median: {sorted(activity_scores)[total_samples//2]:.3f}")
    print(f"  Samples >= 0.7: {sum(1 for s in activity_scores if s >= 0.7)} ({sum(1 for s in activity_scores if s >= 0.7)/total_samples*100:.1f}%)")
    print(f"  Samples >= 0.5: {sum(1 for s in activity_scores if s >= 0.5)} ({sum(1 for s in activity_scores if s >= 0.5)/total_samples*100:.1f}%)")
    print(f"  Samples < 0.5: {sum(1 for s in activity_scores if s < 0.5)} ({sum(1 for s in activity_scores if s < 0.5)/total_samples*100:.1f}%)")

    print(f"\nIS COUNCIL ACTIVITY (0-1):")
    print(f"  Mean: {sum(council_scores)/total_samples:.3f}")
    print(f"  Median: {sorted(council_scores)[total_samples//2]:.3f}")
    print(f"  Samples >= 0.7: {sum(1 for s in council_scores if s >= 0.7)} ({sum(1 for s in council_scores if s >= 0.7)/total_samples*100:.1f}%)")
    print(f"  Samples >= 0.5: {sum(1 for s in council_scores if s >= 0.5)} ({sum(1 for s in council_scores if s >= 0.5)/total_samples*100:.1f}%)")

    # Quality distribution
    high_quality = [s for s in all_samples if s['is_activity_score'] >= 0.7 and s['is_council_score'] >= 0.7]
    medium_quality = [s for s in all_samples if s['is_activity_score'] >= 0.5 and s['is_council_score'] >= 0.5
                      and (s['is_activity_score'] < 0.7 or s['is_council_score'] < 0.7)]
    low_quality = [s for s in all_samples if s['is_activity_score'] < 0.5 or s['is_council_score'] < 0.5]

    print(f"\nQUALITY DISTRIBUTION:")
    print(f"  High quality (both >= 0.7): {len(high_quality)} ({len(high_quality)/total_samples*100:.1f}%)")
    print(f"  Medium quality (both >= 0.5): {len(medium_quality)} ({len(medium_quality)/total_samples*100:.1f}%)")
    print(f"  Low quality (one < 0.5): {len(low_quality)} ({len(low_quality)/total_samples*100:.1f}%)")

    # Issue breakdown
    print(f"\nISSUE BREAKDOWN:")
    issue_counts = {}
    for s in all_samples:
        reason = s['activity_reason']
        issue_counts[reason] = issue_counts.get(reason, 0) + 1

    for reason, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:3d}x: {reason}")

    # Extraction stats by source
    print(f"\n{'='*80}")
    print("EXTRACTION STATS BY SOURCE")
    print(f"{'='*80}")

    for stat in extraction_stats:
        print(f"  {stat['source'][:40]:40s} | Extracted: {stat['total_extracted']:4d} | Sample: {stat['sample_size']:2d}")

    # Save results
    output_file = Path("quality_check_improved_results.json")
    with open(output_file, "w") as f:
        json.dump({
            'samples': all_samples,
            'extraction_stats': extraction_stats,
            'summary': {
                'total_samples': total_samples,
                'activity_mean': sum(activity_scores)/total_samples,
                'council_mean': sum(council_scores)/total_samples,
                'high_quality_count': len(high_quality),
                'medium_quality_count': len(medium_quality),
                'low_quality_count': len(low_quality),
                'issue_counts': issue_counts
            }
        }, f, indent=2)

    print(f"\n{'='*80}")
    print("DETAILED SAMPLES (first 30)")
    print(f"{'='*80}")

    for s in all_samples[:30]:
        print(f"\nSource: {s['source']}")
        print(f"Activity: {s['is_activity_score']:.2f} ({s['activity_reason']})")
        print(f"Council: {s['is_council_score']:.2f} ({s['council_reason']})")
        print(f"Text: {s['text'][:100]}...")
        print("-" * 40)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()