#!/usr/bin/env python3
"""Analyze SDG 17 scores to detect potential bias/overestimation.

This script:
1. Loads alignment results from processed reports
2. Identifies activities with high SDG 17 scores
3. Extracts keywords and patterns from those activities
4. Compares with activities from other SDGs
5. Identifies potential sources of bias (e.g., generic partnership language)
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import SDG_DEFINITIONS
from src.sdg_reference import SDGReference


def load_alignment_results(results_dir: Path) -> List[Dict[str, Any]]:
    """Load all alignment result JSON files from directory."""
    results = []
    json_files = list(results_dir.glob("*_alignment.json"))

    print(f"Loading {len(json_files)} alignment results from {results_dir}...")

    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                result = json.load(f)
                result['_source_file'] = json_file.name
                results.append(result)
        except Exception as e:
            print(f"  Warning: Could not load {json_file}: {e}")

    print(f"  Successfully loaded {len(results)} results")
    return results


def extract_sdg17_activities(
    results: List[Dict[str, Any]],
    score_threshold: float = 0.5,
    top_n: int = 100
) -> List[Dict[str, Any]]:
    """Extract activities with high SDG 17 scores.

    Args:
        results: List of alignment results
        score_threshold: Minimum SDG 17 score to include
        top_n: Maximum number of activities to return

    Returns:
        List of activity dicts with SDG 17 scores
    """
    sdg17_activities = []

    for result in results:
        source = result.get('source', 'Unknown')
        activities = result.get('activities', [])

        for activity in activities:
            sdg_scores = activity.get('sdg_scores', {})
            sdg17_data = sdg_scores.get(17, sdg_scores.get('17', {}))

            if isinstance(sdg17_data, dict):
                score = sdg17_data.get('score', 0)
                is_aligned = sdg17_data.get('is_aligned', False)
            else:
                score = float(sdg17_data) if sdg17_data else 0
                is_aligned = False

            if score >= score_threshold:
                sdg17_activities.append({
                    'text': activity.get('text', activity.get('activity_text', '')),
                    'score': score,
                    'is_aligned': is_aligned,
                    'top_sdg': activity.get('top_sdg', activity.get('top_sdg', 0)),
                    'source': Path(source).stem,
                    'council': result.get('metadata', {}).get('council', 'Unknown'),
                    'year': result.get('metadata', {}).get('year', 'Unknown'),
                    'state': result.get('metadata', {}).get('state', 'Unknown'),
                    'section_type': activity.get('section_type', 'general'),
                    'relevance_score': activity.get('relevance_score', 0)
                })

    # Sort by score descending
    sdg17_activities.sort(key=lambda x: x['score'], reverse=True)

    return sdg17_activities[:top_n]


def extract_keywords(texts: List[str], min_length: int = 4, top_n: int = 50) -> Counter:
    """Extract keywords from texts.

    Uses simple tokenization and filtering.
    Returns most common words/phrases.
    """
    import re

    # Combine all texts
    all_text = ' '.join(texts).lower()

    # Remove punctuation and split
    words = re.findall(r'\b[a-zA-Z]+\b', all_text)

    # Filter out short words and common stop words
    stop_words = {
        'and', 'the', 'for', 'with', 'from', 'that', 'this', 'were', 'been',
        'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may',
        'might', 'must', 'shall', 'can', 'need', 'also', 'each', 'other',
        'which', 'their', 'there', 'where', 'when', 'than', 'more', 'most',
        'some', 'many', 'such', 'only', 'over', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'again',
        'further', 'then', 'once', 'here', 'how', 'what', 'who', 'why',
        'all', 'any', 'both', 'but', 'nor', 'not', 'same', 'so', 'very',
        'just', 'now', 'year', 'council', 'annual', 'report', 'including',
        'new', 'one', 'two', 'first', 'last', 'part', 'based', 'within'
    }

    filtered_words = [w for w in words if len(w) >= min_length and w not in stop_words]

    return Counter(filtered_words).most_common(top_n)


def extract_bigrams(texts: List[str], top_n: int = 30) -> Counter:
    """Extract 2-word phrases from texts."""
    import re

    all_text = ' '.join(texts).lower()
    words = re.findall(r'\b[a-zA-Z]+\b', all_text)

    stop_words = {'and', 'the', 'for', 'with', 'from', 'that', 'this', 'were',
                  'been', 'have', 'has', 'had', 'will', 'would', 'also',
                  'which', 'their', 'there', 'where', 'when', 'than', 'more'}

    # Create bigrams
    bigrams = []
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        if w1 not in stop_words and w2 not in stop_words and len(w1) > 3 and len(w2) > 3:
            bigrams.append(f"{w1} {w2}")

    return Counter(bigrams).most_common(top_n)


def analyze_sdg17_keywords(
    sdg17_activities: List[Dict[str, Any]],
    comparison_activities: Dict[int, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Analyze keywords unique to or overrepresented in SDG 17 activities."""

    sdg17_texts = [a['text'] for a in sdg17_activities]
    sdg17_keywords = extract_keywords(sdg17_texts, top_n=50)
    sdg17_bigrams = extract_bigrams(sdg17_texts, top_n=30)

    # Get keywords for comparison SDGs
    comparison_keywords = {}
    for sdg_num, activities in comparison_activities.items():
        texts = [a['text'] for a in activities[:100]]  # Top 100
        comparison_keywords[sdg_num] = dict(extract_keywords(texts, top_n=30))

    # Find keywords that appear disproportionately in SDG 17
    sdg17_keyword_dict = dict(sdg17_keywords)
    unique_to_sdg17 = []

    for keyword, count in sdg17_keywords[:20]:
        # Check if this keyword appears in other SDGs
        appears_in_others = False
        for sdg_num, kw_dict in comparison_keywords.items():
            if keyword in kw_dict:
                appears_in_others = True
                break

        if not appears_in_others:
            unique_to_sdg17.append((keyword, count))

    return {
        'sdg17_keywords': sdg17_keywords,
        'sdg17_bigrams': sdg17_bigrams,
        'unique_to_sdg17': unique_to_sdg17[:15],
        'sdg17_text_sample': sdg17_texts[:10]
    }


def check_sdg17_indicators(texts: List[str]) -> Dict[str, int]:
    """Check how many SDG 17 specific indicators appear in texts."""

    # SDG 17 indicators from UN
    sdg17_indicators = {
        'finance': ['finance', 'funding', 'funded', 'budget', 'financial', 'investment', 'invest', 'resources'],
        'domestic': ['domestic', 'revenue', 'tax', 'taxation'],
        'oda': ['oda', 'development assistance', 'aid', 'foreign aid', 'development aid'],
        'investment': ['direct investment', 'foreign investment', 'portfolio investment'],
        'debt': ['debt', 'borrowing', 'loans', 'lending', 'credit'],
        'partnership': ['partnership', 'partnerships', 'collaboration', 'collaborate', 'cooperation', 'cooperate'],
        'technology': ['technology', 'technical', 'capacity building', 'knowledge', 'innovation'],
        'trade': ['trade', 'export', 'import', 'tariff', 'market access'],
        'data': ['data', 'statistics', 'statistical', 'information', 'monitoring', 'indicators'],
        'policy': ['policy', 'policies', 'coherent', 'framework', 'systemic', 'institutional']
    }

    indicator_counts = {cat: 0 for cat in sdg17_indicators}

    for text in texts:
        text_lower = text.lower()
        for category, keywords in sdg17_indicators.items():
            if any(kw in text_lower for kw in keywords):
                indicator_counts[category] += 1

    return indicator_counts


def identify_potential_bias(sdg17_activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Identify patterns that might indicate bias/overestimation."""

    analysis = {
        'total_activities': len(sdg17_activities),
        'score_distribution': {},
        'section_types': Counter(),
        'false_positives_suspected': [],
        'bias_indicators': {}
    }

    # Score distribution
    score_ranges = [(0.9, 1.0), (0.8, 0.9), (0.7, 0.8), (0.6, 0.7), (0.5, 0.6)]
    for low, high in score_ranges:
        count = sum(1 for a in sdg17_activities if low <= a['score'] < high)
        analysis['score_distribution'][f"{low:.1f}-{high:.1f}"] = count

    # Section types
    for activity in sdg17_activities:
        analysis['section_types'][activity.get('section_type', 'general')] += 1

    # Check for activities where SDG 17 is top SDG but may not be appropriate
    sdg17_as_top = [a for a in sdg17_activities if a['top_sdg'] == 17]
    analysis['sdg17_is_top_count'] = len(sdg17_as_top)

    # Look for generic partnership language that might trigger false positives
    generic_partnership_terms = [
        'worked with', 'working with', 'work with',
        'partnered with', 'partnership with',
        'collaborated with', 'collaboration with',
        'engaged with', 'engagement with',
        'together with', 'in conjunction with'
    ]

    generic_matches = []
    for activity in sdg17_activities[:50]:  # Check top 50
        text_lower = activity['text'].lower()
        matches = [term for term in generic_partnership_terms if term in text_lower]
        if matches:
            generic_matches.append({
                'text': activity['text'][:150],
                'score': activity['score'],
                'matches': matches
            })

    analysis['generic_partnership_activities'] = generic_matches

    return analysis


def compare_with_sdg_definition(sdg17_activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare activities with official SDG 17 definition."""

    sdg17_info = SDG_DEFINITIONS.get(17, {})

    official_keywords = set()
    for kw_list in [sdg17_info.get('keywords', []),
                    sdg17_info.get('local_gov_keywords', [])]:
        official_keywords.update(kw.lower() for kw in kw_list)

    # Check how many activities contain official keywords
    activities_with_official_kw = 0
    activities_without_official_kw = []

    for activity in sdg17_activities[:100]:
        text_lower = activity['text'].lower()
        if any(kw in text_lower for kw in official_keywords):
            activities_with_official_kw += 1
        else:
            activities_without_official_kw.append({
                'text': activity['text'][:200],
                'score': activity['score']
            })

    return {
        'official_keywords_count': len(official_keywords),
        'activities_with_official_kw': activities_with_official_kw,
        'activities_without_official_kw': len(activities_without_official_kw),
        'sample_without_keywords': activities_without_official_kw[:10],
        'official_keywords_sample': sorted(list(official_keywords))[:30]
    }


def print_report(
    sdg17_activities: List[Dict[str, Any]],
    keyword_analysis: Dict[str, Any],
    bias_analysis: Dict[str, Any],
    sdg17_definition_check: Dict[str, Any]
) -> None:
    """Print comprehensive analysis report."""

    print("\n" + "=" * 80)
    print("SDG 17 BIAS ANALYSIS REPORT")
    print("=" * 80)

    print("\n" + "-" * 80)
    print("1. OVERVIEW")
    print("-" * 80)
    print(f"Total high-scoring SDG 17 activities analyzed: {bias_analysis['total_activities']}")
    print(f"Activities where SDG 17 is the TOP match: {bias_analysis['sdg17_is_top_count']}")
    print(f"\nScore distribution:")
    for range_str, count in bias_analysis['score_distribution'].items():
        bar = "█" * (count // 2)
        print(f"  {range_str}: {count:3d} {bar}")

    print("\n" + "-" * 80)
    print("2. TOP SDG 17 KEYWORDS")
    print("-" * 80)
    print("Most common words in high-scoring SDG 17 activities:")
    for word, count in keyword_analysis['sdg17_keywords'][:20]:
        print(f"  {word:20s}: {count:4d}")

    print("\n" + "-" * 80)
    print("3. TOP SDG 17 BIGRAMS (2-word phrases)")
    print("-" * 80)
    for phrase, count in keyword_analysis['sdg17_bigrams'][:15]:
        print(f"  '{phrase}': {count}")

    print("\n" + "-" * 80)
    print("4. POTENTIAL FALSE POSITIVES - Generic Partnership Language")
    print("-" * 80)
    print(f"Activities with generic partnership terms: {len(bias_analysis['generic_partnership_activities'])}")
    print("\nSample activities that might be false positives:")
    for i, item in enumerate(bias_analysis['generic_partnership_activities'][:5], 1):
        print(f"\n  {i}. [Score: {item['score']:.3f}] Matches: {', '.join(item['matches'])}")
        print(f"     Text: {item['text']}...")

    print("\n" + "-" * 80)
    print("5. COMPARISON WITH OFFICIAL SDG 17 DEFINITION")
    print("-" * 80)
    print(f"Activities containing official SDG 17 keywords: {sdg17_definition_check['activities_with_official_kw']}")
    print(f"Activities WITHOUT official keywords: {sdg17_definition_check['activities_without_official_kw']}")
    print(f"\nSample activities lacking official keywords (potential false positives):")
    for i, item in enumerate(sdg17_definition_check['sample_without_keywords'][:5], 1):
        print(f"\n  {i}. [Score: {item['score']:.3f}]")
        print(f"     Text: {item['text']}...")

    print("\n" + "-" * 80)
    print("6. SDG 17 INDICATOR CATEGORIES")
    print("-" * 80)
    sdg17_texts = [a['text'] for a in sdg17_activities]
    indicator_counts = check_sdg17_indicators(sdg17_texts)
    print("Distribution of SDG 17 specific indicators in high-scoring activities:")
    for category, count in sorted(indicator_counts.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * (count // 3)
        print(f"  {category:15s}: {count:4d} {bar}")

    print("\n" + "-" * 80)
    print("7. SAMPLE HIGH-SCORING ACTIVITIES")
    print("-" * 80)
    print("Top 10 activities by SDG 17 score:")
    for i, activity in enumerate(sdg17_activities[:10], 1):
        top_sdg_marker = "★" if activity['top_sdg'] == 17 else " "
        print(f"\n  {i}. [{activity['score']:.3f}] {top_sdg_marker} {activity['council']} ({activity['year']})")
        print(f"     {activity['text'][:200]}...")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nINTERPRETATION GUIDE:")
    print("- Activities with generic 'worked with' or 'partnership' language may be false positives")
    print("- Check if activities lack specific SDG 17 keywords (finance, ODA, technology transfer, etc.)")
    print("- High scores with generic language suggest the model may over-weight partnership terms")
    print("- Compare section types - SDG 17 activities concentrated in certain sections may indicate bias")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze SDG 17 scores for potential bias/overestimation"
    )
    parser.add_argument(
        "--results-dir", "-r",
        default="results/by_council",
        help="Directory containing alignment result JSON files"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.5,
        help="Minimum SDG 17 score to analyze (default: 0.5)"
    )
    parser.add_argument(
        "--top-n", "-n",
        type=int,
        default=100,
        help="Number of top-scoring activities to analyze (default: 100)"
    )
    parser.add_argument(
        "--output", "-o",
        default="sdg17_bias_analysis.txt",
        help="Output file for detailed report"
    )

    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)

    # Load results
    results = load_alignment_results(results_dir)
    if not results:
        print("No alignment results found to analyze.")
        sys.exit(1)

    # Extract high-scoring SDG 17 activities
    print(f"\nExtracting activities with SDG 17 score >= {args.threshold}...")
    sdg17_activities = extract_sdg17_activities(results, args.threshold, args.top_n)
    print(f"  Found {len(sdg17_activities)} activities")

    if not sdg17_activities:
        print("No high-scoring SDG 17 activities found.")
        sys.exit(0)

    # Get comparison activities from other SDGs
    print("\nLoading comparison activities from other SDGs...")
    comparison_activities = {}
    for sdg_num in [1, 3, 7, 11, 13, 15]:  # Sample of other SDGs
        activities = []
        for result in results:
            for activity in result.get('activities', []):
                sdg_scores = activity.get('sdg_scores', {})
                sdg_data = sdg_scores.get(sdg_num, sdg_scores.get(str(sdg_num), {}))
                if isinstance(sdg_data, dict) and sdg_data.get('score', 0) >= 0.5:
                    activities.append(activity)
        comparison_activities[sdg_num] = activities[:50]  # Top 50
        print(f"  SDG {sdg_num}: {len(comparison_activities[sdg_num])} high-scoring activities")

    # Analyze keywords
    print("\nAnalyzing keywords...")
    keyword_analysis = analyze_sdg17_keywords(sdg17_activities, comparison_activities)

    # Identify potential bias
    print("Identifying potential bias patterns...")
    bias_analysis = identify_potential_bias(sdg17_activities)

    # Check against SDG definition
    print("Checking against official SDG 17 definition...")
    sdg17_definition_check = compare_with_sdg_definition(sdg17_activities)

    # Print report
    print_report(sdg17_activities, keyword_analysis, bias_analysis, sdg17_definition_check)

    # Save detailed report to file
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        f.write("SDG 17 BIAS ANALYSIS - DETAILED REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write("ALL HIGH-SCORING SDG 17 ACTIVITIES:\n")
        f.write("-" * 80 + "\n")
        for i, activity in enumerate(sdg17_activities, 1):
            f.write(f"\n{i}. Score: {activity['score']:.4f} | "
                   f"Top SDG: {activity['top_sdg']} | "
                   f"Council: {activity['council']} | Year: {activity['year']}\n")
            f.write(f"   Section: {activity['section_type']} | "
                   f"Relevance: {activity['relevance_score']:.3f}\n")
            f.write(f"   Text: {activity['text']}\n")
            f.write("-" * 80 + "\n")

    print(f"\nDetailed report saved to: {output_path}")


if __name__ == "__main__":
    main()
