#!/usr/bin/env python3
"""
Activity Extraction Quality Assessment Script

Enables data-driven iterative improvement of activity extraction by:
1. Random sampling of annual reports and activity text
2. Automated quality rating on two dimensions
3. Issue categorization and pattern identification
4. Comparison across iterations to validate improvements
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import Counter

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.activity_extractor import ActivityExtractor


@dataclass
class QualityRating:
    """Quality rating for a single activity sample."""
    source: str
    text: str
    text_length: int
    word_count: int
    is_activity_score: float
    is_council_score: float
    activity_reason: str
    council_reason: str
    avg_confidence: float
    confidence: float
    issue_category: str


@dataclass
class QualityResults:
    """Results from a quality assessment run."""
    timestamp: str
    sample_size: int
    num_pdfs: int
    total_samples: int
    is_activity_mean: float
    is_activity_median: float
    is_council_mean: float
    is_council_median: float
    high_quality_count: int
    high_quality_pct: float
    medium_quality_count: int
    medium_quality_pct: float
    low_quality_count: int
    low_quality_pct: float
    issue_breakdown: Dict[str, int]
    samples: List[Dict]


# Quality rating heuristics - expanded verb lists
# These are derived from actual low-quality samples analysis
ACTION_VERBS_PAST = [
    'completed', 'implemented', 'delivered', 'constructed', 'built',
    'established', 'created', 'launched', 'initiated', 'introduced',
    'developed', 'installed', 'upgraded', 'renewed', 'refurbished',
    'purchased', 'acquired', 'commissioned', 'opened', 'started',
    'appointed', 'awarded', 'granted', 'funded', 'hosted', 'held',
    'conducted', 'undertook', 'achieved', 'performed', 'provided',
    # Additional verbs found in council activities
    'partnered', 'supported', 'received', 'recognition', 'awarded',
    'hosted', 'attended', 'participated', 'presented', 'recognized',
    'sponsored', 'organized', 'delivered', 'facilitated', 'coordinated',
    'attracted', 'secured', 'enhanced', 'expanded', 'improved', 'increased',
    'reduced', 'decreased', 'maintained', 'preserved', 'protected',
    'conserved', 'monitored', 'assessed', 'evaluated', 'reviewed',
    'adopted', 'approved', 'endorsed', 'signed', 'appointed',
    'trained', 'educated', 'informed', 'communicated', 'published',
    'distributed', 'shared', 'collaborated', 'engaged', 'connected',
    'networking', 'networking', 'visited', 'toured', 'inspected',
    'investigated', 'audited', 'inspected', 'certified', 'renewed',
    'upgraded', 'modernized', 'automated', 'digitized', 'upskilled'
]

ACTION_VERBS_PRESENT = [
    'implements', 'delivers', 'provides', 'supports', 'offers',
    'operates', 'manages', 'coordinates', 'facilitates', 'runs',
    'supports', 'hosts', 'organizes', 'facilitates', 'delivers',
    'coordinates', 'collaborates', 'engages', 'partners', 'advocates',
    'drives', 'leads', 'promotes', 'raises', 'enhances', 'improves',
    'increases', 'reduces', 'maintains', 'preserves', 'protects',
    'monitors', 'assesses', 'evaluates', 'reviews', 'approves',
    'adopts', 'provides', 'delivers', 'offers', 'enables', 'empowers'
]

# Verbs that indicate policy/planning statements rather than completed activities
POLICY_VERBS = [
    'will', 'will be', 'will continue', 'will undertake', 'will support',
    'to be', 'to undertake', 'to provide', 'to deliver', 'to develop',
    'planned to', 'scheduled to', 'expected to', 'proposed to',
    'intends to', 'aims to', 'seeks to', 'endeavours to', 'will endeavour'
]

FINANCIAL_PATTERNS = [
    'fair value', 'carrying value', 'impairment', 'depreciation',
    'balance date', 'financial statements', 'recoverable amount',
    'valuation inputs', 'asset class', 'material impact'
]

POLICY_PATTERNS = [
    'action plan', 'priority area', 'key deliverable', 'strategic objective',
    'will be', 'will continue', 'to be', 'planned to', 'scheduled to'
]

COUNCIL_WORDS = ['council', 'shire', 'city', 'municipality', 'we ', 'our ']

COUNCIL_SERVICES = [
    'library', 'child care', 'aged care', 'meals on wheels', 'waste',
    'recycling', 'road', 'footpath', 'drainage', 'park', 'reserve',
    'community centre', 'hall', 'swimming pool', 'sport', 'recreation',
    'planning permit', 'parking', 'ranger', 'animal', 'health inspection'
]

NON_COUNCIL = ['nbn', 'telstra', 'state government', 'federal', 'commonwealth']


def get_random_pdfs(data_dir: Path, n: int = 20, seed: int = 42) -> List[Path]:
    """Get n random PDFs from data directory."""
    random.seed(seed)
    all_pdfs = list(data_dir.rglob("*.pdf"))
    if len(all_pdfs) < n:
        print(f"Warning: Only {len(all_pdfs)} PDFs found, requested {n}")
        n = len(all_pdfs)
    selected = random.sample(all_pdfs, n)
    return selected


def extract_activities(pdf_path: Path, use_nofinancial: bool = True) -> List[Dict]:
    """Extract activities from a PDF file."""
    extractor = ActivityExtractor(
        min_activity_length=5,
        max_activity_length=150,
        use_llm_labeling=False,
        use_sentence_reconstruction=True,
        nofinancial=use_nofinancial
    )
    result = extractor.extract_from_pdf(pdf_path)
    return result.get("activities", [])


def sample_activities(activities: List[Dict], sample_rate: float = 0.05, seed: int = 42,
                      min_samples: int = 3, max_samples: int = 15) -> List[Dict]:
    """Sample activities with configurable bounds."""
    random.seed(seed)
    n_samples = max(min_samples, min(max_samples, int(len(activities) * sample_rate)))
    if len(activities) <= n_samples:
        return activities
    return random.sample(activities, n_samples)


def categorize_issue(text_lower: str, has_past_action: bool, has_present_action: bool,
                     has_financial: bool, has_policy: bool, has_council: bool,
                     is_activity: float) -> str:
    """Categorize the type of issue for this sample."""
    if has_financial:
        return "financial"
    elif has_policy and not has_past_action:
        return "policy"
    elif is_activity < 0.5 and not has_past_action and not has_present_action:
        return "generic"
    elif any(future in text_lower for future in ['will ', 'planned to', 'scheduled to']):
        return "future"
    elif is_activity < 0.5:
        return "incomplete"
    return "none"


def has_future_marker(text_lower: str) -> bool:
    """Check for future/planning markers."""
    # Check for "will" as a standalone word (not part of another word)
    import re
    # Match "will" as standalone word followed by verb
    if re.search(r'\bwill\b', text_lower):
        return True
    # Check policy verb patterns
    for verb in POLICY_VERBS:
        if verb in text_lower:
            return True
    return False


def rate_activity(text: str) -> Tuple[float, float, str, str, str]:
    """
    Rate an activity text on two criteria.

    Returns:
        Tuple of (is_activity_score, is_council_score, activity_reason, council_reason, issue_category)
    """
    text_lower = text.lower()

    # Check for activity
    has_past_action = any(verb in text_lower for verb in ACTION_VERBS_PAST)
    has_present_action = any(verb in text_lower for verb in ACTION_VERBS_PRESENT)
    has_financial = any(pattern in text_lower for pattern in FINANCIAL_PATTERNS)
    has_policy = any(pattern in text_lower for pattern in POLICY_PATTERNS)
    has_council = any(word in text_lower for word in COUNCIL_WORDS)
    has_future = has_future_marker(text_lower)

    # Activity scoring with future action handling
    if has_financial:
        is_activity = 0.2
        activity_reason = "Financial/accounting text"
    elif has_future and not has_past_action:
        # Future/planned actions get lower scores
        if has_past_action:
            is_activity = 0.7
            activity_reason = "Mixed: has past action but also future markers"
        else:
            is_activity = 0.35
            activity_reason = "Future/planned action, not completed"
    elif has_policy and not has_past_action:
        is_activity = 0.35
        activity_reason = "Policy/plan statement"
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

    # Council scoring
    has_council_service = any(service in text_lower for service in COUNCIL_SERVICES)
    has_non_council = any(word in text_lower for word in NON_COUNCIL)

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

    # Categorize issue
    issue_category = categorize_issue(
        text_lower, has_past_action, has_present_action,
        has_financial, has_policy, has_council, is_activity
    )

    return is_activity, is_council, activity_reason, council_reason, issue_category


def classify_quality(is_activity: float, is_council: float) -> str:
    """Classify sample into quality tier."""
    if is_activity >= 0.7 and is_council >= 0.7:
        return "high"
    elif is_activity >= 0.5 and is_council >= 0.5:
        return "medium"
    else:
        return "low"


def run_assessment(
    data_dir: Path,
    sample_size: int = 20,
    sample_rate: float = 0.05,
    seed: int = 42,
    use_nofinancial: bool = True,
    output_dir: Optional[Path] = None
) -> QualityResults:
    """Run full quality assessment."""
    print("=" * 80)
    print("ACTIVITY EXTRACTION QUALITY ASSESSMENT")
    print("=" * 80)

    # Select random PDFs
    print(f"\nSelecting {sample_size} random PDFs (seed={seed})...")
    pdfs = get_random_pdfs(data_dir, n=sample_size, seed=seed)

    print(f"\nSelected PDFs:")
    for i, pdf in enumerate(pdfs, 1):
        print(f"  {i:2d}. {pdf.relative_to(data_dir)}")

    # Extract and sample activities
    all_samples = []
    extraction_stats = []

    for pdf_path in pdfs:
        print(f"\nProcessing: {pdf_path.name}")

        try:
            activities = extract_activities(pdf_path, use_nofinancial=use_nofinancial)
            total_extracted = len(activities)
            print(f"  Extracted: {total_extracted} activities")

            # Sample activities
            samples = sample_activities(activities, sample_rate=sample_rate, seed=seed)
            print(f"  Sampled: {len(samples)} for review")

            extraction_stats.append({
                'source': pdf_path.name,
                'total_extracted': total_extracted,
                'sample_size': len(samples)
            })

            for i, activity in enumerate(samples, 1):
                text = activity.get("text", "")
                (is_activity, is_council, act_reason,
                 council_reason, issue_cat) = rate_activity(text)

                rating = QualityRating(
                    source=pdf_path.name,
                    text=text,
                    text_length=len(text),
                    word_count=len(text.split()),
                    is_activity_score=is_activity,
                    is_council_score=is_council,
                    activity_reason=act_reason,
                    council_reason=council_reason,
                    avg_confidence=(is_activity + is_council) / 2,
                    confidence=activity.get("relevance_score", 0.5),
                    issue_category=issue_cat
                )
                all_samples.append(asdict(rating))

        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    # Calculate statistics
    total = len(all_samples)
    if total == 0:
        raise ValueError("No samples extracted!")

    activity_scores = [s['is_activity_score'] for s in all_samples]
    council_scores = [s['is_council_score'] for s in all_samples]

    # Quality tiers
    high_quality = [s for s in all_samples if classify_quality(s['is_activity_score'], s['is_council_score']) == 'high']
    medium_quality = [s for s in all_samples if classify_quality(s['is_activity_score'], s['is_council_score']) == 'medium']
    low_quality = [s for s in all_samples if classify_quality(s['is_activity_score'], s['is_council_score']) == 'low']

    # Issue breakdown
    issue_counts = Counter(s['issue_category'] for s in all_samples)

    results = QualityResults(
        timestamp=datetime.now().isoformat(),
        sample_size=sample_size,
        num_pdfs=len(pdfs),
        total_samples=total,
        is_activity_mean=sum(activity_scores) / total,
        is_activity_median=sorted(activity_scores)[total // 2],
        is_council_mean=sum(council_scores) / total,
        is_council_median=sorted(council_scores)[total // 2],
        high_quality_count=len(high_quality),
        high_quality_pct=len(high_quality) / total * 100,
        medium_quality_count=len(medium_quality),
        medium_quality_pct=len(medium_quality) / total * 100,
        low_quality_count=len(low_quality),
        low_quality_pct=len(low_quality) / total * 100,
        issue_breakdown=dict(issue_counts),
        samples=all_samples
    )

    return results


def print_report(results: QualityResults, prev_results: Optional[QualityResults] = None):
    """Print assessment report to console."""
    print("\n" + "=" * 80)
    print("QUALITY ASSESSMENT REPORT")
    print("=" * 80)
    print(f"\nTimestamp: {results.timestamp}")
    print(f"Sample: {results.num_pdfs} PDFs, {results.total_samples} total samples")

    # Comparison with previous iteration
    if prev_results:
        print("\n--- COMPARISON WITH PREVIOUS ITERATION ---")
        diff = results.low_quality_pct - prev_results.low_quality_pct
        arrow = "↓" if diff < 0 else "↑" if diff > 0 else "→"
        print(f"Low Quality Rate: {prev_results.low_quality_pct:.1f}% → {results.low_quality_pct:.1f}% {arrow} ({diff:+.1f}pp)")

        diff = results.high_quality_pct - prev_results.high_quality_pct
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
        print(f"High Quality Rate: {prev_results.high_quality_pct:.1f}% → {results.high_quality_pct:.1f}% {arrow} ({diff:+.1f}pp)")

        diff = results.is_activity_mean - prev_results.is_activity_mean
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
        print(f"Is Activity Mean: {prev_results.is_activity_mean:.3f} → {results.is_activity_mean:.3f} {arrow} ({diff:+.3f})")

    print("\n--- OVERALL METRICS ---")
    print(f"\nIs Activity Text (0-1):")
    print(f"  Mean: {results.is_activity_mean:.3f}")
    print(f"  Median: {results.is_activity_median:.3f}")
    print(f"  Samples ≥ 0.7: {sum(1 for s in results.samples if s['is_activity_score'] >= 0.7)}")
    print(f"  Samples < 0.5: {sum(1 for s in results.samples if s['is_activity_score'] < 0.5)}")

    print(f"\nIs Council Activity (0-1):")
    print(f"  Mean: {results.is_council_mean:.3f}")
    print(f"  Median: {results.is_council_median:.3f}")
    print(f"  Samples ≥ 0.7: {sum(1 for s in results.samples if s['is_council_score'] >= 0.7)}")

    print(f"\n--- QUALITY DISTRIBUTION ---")
    print(f"  High Quality (both ≥ 0.7): {results.high_quality_count} ({results.high_quality_pct:.1f}%)")
    print(f"  Medium Quality (both ≥ 0.5): {results.medium_quality_count} ({results.medium_quality_pct:.1f}%)")
    print(f"  Low Quality (either < 0.5): {results.low_quality_count} ({results.low_quality_pct:.1f}%)")

    print(f"\n--- ISSUE BREAKDOWN ---")
    for reason, count in sorted(results.issue_breakdown.items(), key=lambda x: -x[1]):
        pct = count / results.total_samples * 100
        print(f"  {count:3d} ({pct:5.1f}%): {reason}")

    # Show low-quality examples
    low_quality_samples = [s for s in results.samples if s['issue_category'] != 'none']
    if low_quality_samples:
        print(f"\n--- LOW-QUALITY EXAMPLES (first 10) ---")
        for s in low_quality_samples[:10]:
            print(f"\n  Source: {s['source']}")
            print(f"  Issue: {s['issue_category']} | Activity: {s['is_activity_score']:.2f} | Council: {s['is_council_score']:.2f}")
            print(f"  Text: {s['text'][:100]}...")


def save_results(results: QualityResults, output_dir: Path):
    """Save results to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = output_dir / "results.json"
    with open(json_path, 'w') as f:
        json.dump(asdict(results), f, indent=2)

    # Save markdown report
    report_path = output_dir / "report.md"
    with open(report_path, 'w') as f:
        f.write(f"# Activity Extraction Quality Assessment\n\n")
        f.write(f"**Timestamp:** {results.timestamp}\n")
        f.write(f"**Sample:** {results.num_pdfs} PDFs, {results.total_samples} total samples\n\n")

        f.write(f"## Quality Distribution\n\n")
        f.write(f"| Quality Level | Count | Percentage |\n")
        f.write(f"|---------------|-------|------------|\n")
        f.write(f"| High (both ≥ 0.7) | {results.high_quality_count} | {results.high_quality_pct:.1f}% |\n")
        f.write(f"| Medium (both ≥ 0.5) | {results.medium_quality_count} | {results.medium_quality_pct:.1f}% |\n")
        f.write(f"| Low (either < 0.5) | {results.low_quality_count} | {results.low_quality_pct:.1f}% |\n\n")

        f.write(f"## Issue Breakdown\n\n")
        f.write(f"| Issue Type | Count | Percentage |\n")
        f.write(f"|-------------|-------|------------|\n")
        for reason, count in sorted(results.issue_breakdown.items(), key=lambda x: -x[1]):
            pct = count / results.total_samples * 100
            f.write(f"| {reason} | {count} | {pct:.1f}% |\n")

        f.write(f"\n## Recommendations\n\n")
        if results.issue_breakdown.get('financial', 0) > 5:
            f.write(f"- **Financial text**: Add patterns to `src/text_processor.py` → `financial_markers`\n")
        if results.issue_breakdown.get('policy', 0) > 5:
            f.write(f"- **Policy statements**: Add patterns to `src/text_processor.py` → `policy_markers`\n")
        if results.issue_breakdown.get('generic', 0) > 5:
            f.write(f"- **Generic descriptions**: Consider adding action verbs to `priority_verbs` or `standard_verbs`\n")
        if results.issue_breakdown.get('future', 0) > 5:
            f.write(f"- **Future actions**: Add to `weak_verbs` or `policy_markers`\n")

    print(f"\nResults saved to: {output_dir}")
    print(f"  - {json_path}")
    print(f"  - {report_path}")


def load_previous_results(json_path: Path) -> QualityResults:
    """Load previous iteration results for comparison."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    # Convert back to dataclass
    return QualityResults(**data)


def main():
    parser = argparse.ArgumentParser(description="Activity Extraction Quality Assessment")
    parser.add_argument("--data-dir", type=Path, default=Path("data/LGAcleannames"),
                        help="Directory containing PDF annual reports")
    parser.add_argument("--sample-size", type=int, default=20,
                        help="Number of PDFs to sample")
    parser.add_argument("--sample-rate", type=float, default=0.05,
                        help="Percentage of activities to sample per PDF (0.05 = 5%%)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    parser.add_argument("--nofinancial", action="store_true", default=True,
                        help="Exclude financial statements (default: True)")
    parser.add_argument("--include-financial", action="store_false", dest="nofinancial",
                        help="Include financial statements")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory for results (default: quality_iteration_N)")
    parser.add_argument("--compare-with", type=Path, default=None,
                        help="Path to previous results JSON for comparison")

    args = parser.parse_args()

    # Determine output directory
    if args.output_dir is None:
        # Auto-generate iteration directory
        base_dir = PROJECT_ROOT / "quality_assessment"
        existing = list(base_dir.glob("iteration_*"))
        next_num = len(existing) + 1
        args.output_dir = base_dir / f"iteration_{next_num:02d}"

    # Load previous results if specified
    prev_results = None
    if args.compare_with and args.compare_with.exists():
        prev_results = load_previous_results(args.compare_with)

    # Run assessment
    results = run_assessment(
        data_dir=args.data_dir,
        sample_size=args.sample_size,
        sample_rate=args.sample_rate,
        seed=args.seed,
        use_nofinancial=args.nofinancial,
        output_dir=args.output_dir
    )

    # Print report
    print_report(results, prev_results)

    # Save results
    save_results(results, args.output_dir)

    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0)
