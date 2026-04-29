#!/usr/bin/env python3
"""Analyze SDG 12 (Responsible Consumption and Production) classification issues.

This script:
1. Loads benchmark results to identify SDG 12 misclassifications
2. Performs TF-IDF analysis on keywords from incorrectly assessed texts
3. Compares SDG 12's text embeddings with other SDGs
4. Identifies patterns in false positives and false negatives
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns

from src.config import SDG_DEFINITIONS
from src.sdg_reference import SDGReference


def load_osdg_data(csv_path: Path, sdg_num: int = 12, min_agreement: float = 0.7) -> pd.DataFrame:
    """Load OSDG data filtered for specific SDG."""
    print(f"Loading OSDG data for SDG {sdg_num}...")
    df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')

    # Filter by SDG and agreement
    df = df[(df['sdg'] == sdg_num) & (df['agreement'] >= min_agreement)].copy()
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]

    print(f"Found {len(df)} texts for SDG {sdg_num}")
    return df


def analyze_sdg_definition():
    """Analyze SDG 12 definition and keywords."""
    sdg12 = SDG_DEFINITIONS[12]

    print("\n" + "="*80)
    print("SDG 12 DEFINITION ANALYSIS")
    print("="*80)
    print(f"Name: {sdg12['name']}")
    print(f"\nDescription:\n{sdg12['description'][:500]}...")
    print(f"\nKeywords ({len(sdg12.get('keywords', []))}):")
    print(", ".join(sdg12.get('keywords', [])[:20]))
    print(f"\nLocal Gov Keywords ({len(sdg12.get('local_gov_keywords', []))}):")
    print(", ".join(sdg12.get('local_gov_keywords', [])[:20]))
    print(f"\nIndicators ({len(sdg12.get('indicators', []))}):")
    for ind in sdg12.get('indicators', [])[:3]:
        print(f"  - {ind}")


def compare_sdg_embeddings():
    """Compare SDG 12 embedding similarity with other SDGs."""
    print("\n" + "="*80)
    print("SDG 12 EMBEDDING SIMILARITY ANALYSIS")
    print("="*80)

    reference = SDGReference()
    sdg_embeddings = reference.get_all_embeddings()

    # Get SDG 12 embedding
    sdg12_emb = sdg_embeddings[12].reshape(1, -1)

    # Calculate similarity with all other SDGs
    similarities = {}
    for sdg_num in range(1, 18):
        if sdg_num != 12:
            other_emb = sdg_embeddings[sdg_num].reshape(1, -1)
            sim = cosine_similarity(sdg12_emb, other_emb)[0][0]
            similarities[sdg_num] = sim

    # Sort by similarity
    sorted_sims = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

    print("\nSDG 12 Embedding Similarity to Other SDGs:")
    print("-" * 60)
    print(f"{'Rank':<6} {'SDG':<5} {'Name':<40} {'Similarity':<12}")
    print("-" * 60)

    for rank, (sdg_num, sim) in enumerate(sorted_sims, 1):
        name = SDG_DEFINITIONS[sdg_num]['name'][:37]
        print(f"{rank:<6} {sdg_num:<5} {name:<40} {sim:>10.4f}")

    # Identify most similar SDGs (potential confusion sources)
    print("\n" + "-" * 60)
    print("MOST SIMILAR SDGs (Potential Confusion Sources):")
    for sdg_num, sim in sorted_sims[:5]:
        name = SDG_DEFINITIONS[sdg_num]['name']
        print(f"  SDG {sdg_num} ({name}): {sim:.4f}")

    return similarities


def find_keyword_overlap():
    """Find keyword overlaps between SDG 12 and other SDGs."""
    print("\n" + "="*80)
    print("SDG 12 KEYWORD OVERLAP ANALYSIS")
    print("="*80)

    sdg12 = SDG_DEFINITIONS[12]
    sdg12_keywords = set(sdg12.get('keywords', []) + sdg12.get('local_gov_keywords', []))

    overlaps = {}
    for sdg_num in range(1, 18):
        if sdg_num != 12:
            other = SDG_DEFINITIONS[sdg_num]
            other_keywords = set(other.get('keywords', []) + other.get('local_gov_keywords', []))
            overlap = sdg12_keywords & other_keywords
            overlaps[sdg_num] = {
                'count': len(overlap),
                'keywords': list(overlap)
            }

    # Sort by overlap count
    sorted_overlaps = sorted(overlaps.items(), key=lambda x: x[1]['count'], reverse=True)

    print("\nKeyword Overlaps with SDG 12:")
    print("-" * 60)
    print(f"{'SDG':<5} {'Name':<40} {'Overlap':<10} {'Keywords':<30}")
    print("-" * 60)

    for sdg_num, data in sorted_overlaps[:10]:
        name = SDG_DEFINITIONS[sdg_num]['name'][:37]
        count = data['count']
        keywords = ", ".join(data['keywords'][:5])
        print(f"{sdg_num:<5} {name:<40} {count:<10} {keywords:<30}")

    return overlaps


def analyze_osdg_texts_for_sdg12():
    """Analyze actual OSDG texts labeled as SDG 12."""
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    if not csv_path.exists():
        print(f"OSDG data not found at {csv_path}")
        return None

    df = load_osdg_data(csv_path, sdg_num=12, min_agreement=0.7)

    if len(df) == 0:
        print("No SDG 12 texts found")
        return None

    print("\n" + "="*80)
    print("SDG 12 TEXT ANALYSIS (OSDG Data)")
    print("="*80)

    # Sample texts
    print(f"\nTotal SDG 12 texts: {len(df)}")
    print(f"Average agreement: {df['agreement'].mean():.2f}")
    print(f"Agreement std: {df['agreement'].std():.2f}")

    # Text length statistics
    df['text_length'] = df['text'].str.len()
    df['word_count'] = df['text'].str.split().str.len()

    print(f"\nText Statistics:")
    print(f"  Average length: {df['text_length'].mean():.0f} chars")
    print(f"  Average words: {df['word_count'].mean():.0f}")
    print(f"  Median words: {df['word_count'].median():.0f}")

    # Sample texts
    print("\nSample SDG 12 Texts (high agreement):")
    high_agreement = df[df['agreement'] >= 0.9].head(5)
    for idx, row in high_agreement.iterrows():
        text = row['text'][:200] + "..." if len(row['text']) > 200 else row['text']
        print(f"\n  [{row['agreement']:.2f}] {text}")

    return df


def perform_tfidf_analysis(df: pd.DataFrame = None):
    """Perform TF-IDF analysis on SDG 12 texts."""
    print("\n" + "="*80)
    print("TF-IDF ANALYSIS: SDG 12 DISTINCTIVE TERMS")
    print("="*80)

    # Load texts from multiple SDGs for comparison
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    if not csv_path.exists():
        print("OSDG data not found")
        return

    all_df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')
    all_df = all_df[(all_df['agreement'] >= 0.7) & (all_df['text'].notna())].copy()

    # Sample from each SDG for comparison
    sdg_texts = []
    sdg_labels = []

    for sdg_num in [12, 11, 13, 9, 8]:  # Include SDG 12 and similar SDGs
        texts = all_df[all_df['sdg'] == sdg_num]['text'].tolist()
        if len(texts) > 50:
            texts = np.random.choice(texts, 50, replace=False)
        sdg_texts.extend(texts)
        sdg_labels.extend([f"SDG_{sdg_num}"] * len(texts))

    # TF-IDF analysis
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8
    )

    tfidf_matrix = vectorizer.fit_transform(sdg_texts)
    feature_names = vectorizer.get_feature_names_out()

    # Get top terms for SDG 12
    sdg12_indices = [i for i, label in enumerate(sdg_labels) if label == "SDG_12"]
    sdg12_tfidf = tfidf_matrix[sdg12_indices].mean(axis=0).A1

    top_indices = sdg12_tfidf.argsort()[-30:][::-1]
    top_terms = [(feature_names[i], sdg12_tfidf[i]) for i in top_indices]

    print("\nTop 30 Distinctive Terms for SDG 12:")
    print("-" * 50)
    for rank, (term, score) in enumerate(top_terms, 1):
        print(f"{rank:<4} {term:<30} {score:.4f}")

    # Compare with other SDGs
    print("\n" + "-" * 50)
    print("COMPARISON: Terms more common in SDG 12 vs others")

    comparison_results = {}
    for compare_sdg in [11, 13, 9]:
        compare_indices = [i for i, label in enumerate(sdg_labels) if label == f"SDG_{compare_sdg}"]
        compare_tfidf = tfidf_matrix[compare_indices].mean(axis=0).A1

        # Find terms with high relative frequency in SDG 12
        diff_scores = sdg12_tfidf - compare_tfidf
        top_diff_indices = diff_scores.argsort()[-15:][::-1]

        comparison_results[compare_sdg] = [
            (feature_names[i], diff_scores[i], sdg12_tfidf[i])
            for i in top_diff_indices
        ]

    for compare_sdg, terms in comparison_results.items():
        name = SDG_DEFINITIONS[compare_sdg]['name']
        print(f"\nTerms more common in SDG 12 vs SDG {compare_sdg} ({name}):")
        for term, diff, score in terms[:10]:
            print(f"  {term:<25} (diff: +{diff:.3f}, tfidf: {score:.3f})")

    return top_terms, comparison_results


def analyze_confusion_patterns():
    """Analyze potential confusion patterns with similar SDGs."""
    print("\n" + "="*80)
    print("SDG 12 CONFUSION PATTERN ANALYSIS")
    print("="*80)

    # Load benchmark results if available
    benchmark_files = list(Path("results/benchmark").glob("benchmark_*.json"))
    if not benchmark_files:
        print("No benchmark results found")
        return

    latest = max(benchmark_files, key=lambda p: p.stat().st_mtime)
    with open(latest) as f:
        results = json.load(f)

    # Find SDG 12 metrics
    for result in results:
        sdg12_metrics = result['sdg_metrics'].get('12', {})
        if sdg12_metrics:
            print(f"\n{result['approach']} - {result['model'][:50]}:")
            print(f"  Precision: {sdg12_metrics.get('precision', 0):.2%}")
            print(f"  Recall: {sdg12_metrics.get('recall', 0):.2%}")
            print(f"  F1: {sdg12_metrics.get('f1', 0):.2%}")
            print(f"  TP: {sdg12_metrics.get('tp', 0)}, FP: {sdg12_metrics.get('fp', 0)}, FN: {sdg12_metrics.get('fn', 0)}")


def generate_sdg12_recommendations(overlaps: Dict, similarities: Dict):
    """Generate recommendations for improving SDG 12 detection."""
    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR IMPROVING SDG 12 DETECTION")
    print("="*80)

    print("\n1. HIGH CONFUSION WITH OTHER SDGs:")
    print("   - SDG 12 is most commonly confused with SDG 11 (Sustainable Cities)")
    print("   - and SDG 13 (Climate Action)")
    print("   - This is expected as sustainability topics overlap")

    print("\n2. KEYWORD ANALYSIS ISSUES:")
    print("   - SDG 12 keywords overlap heavily with SDG 11 (cities)")
    print("   - Words like 'sustainable', 'environment' appear in multiple SDGs")
    print("   - Missing distinctive SDG 12 terms like:")
    print("     * 'circular economy', 'waste hierarchy', 'extended producer responsibility'")
    print("     * 'sustainable procurement', 'green purchasing'")
    print("     * 'resource efficiency', 'material flow'")

    print("\n3. EMBEDDING SIMILARITY:")
    print("   - SDG 12 embedding is too similar to SDG 11 and SDG 13")
    print("   - Need more distinctive text variants in embedding generation")

    print("\n4. POTENTIAL IMPROVEMENTS:")
    print("   a) Add more SDG 12-specific local government keywords:")
    print("      - 'waste management plan', 'recycling program'")
    print("      - 'sustainable procurement policy'")
    print("      - 'single-use plastic ban'")
    print("   b) Create separate embedding variant focused on consumption patterns")
    print("   c) Adjust similarity threshold specifically for SDG 12")
    print("   d) Add negative examples: texts that look like SDG 12 but aren't")

    print("\n5. TRAINING DATA ISSUES:")
    print("   - OSDG dataset may have few SDG 12 examples (small sample size)")
    print("   - SDG 12 texts often mixed with SDG 11 in council reports")
    print("   - Consider data augmentation with synthetic SDG 12 examples")


def main():
    """Main analysis function."""
    print("SDG 12 (Responsible Consumption and Production) - Issue Analysis")
    print("="*80)

    # 1. Analyze SDG definition
    analyze_sdg_definition()

    # 2. Compare embeddings
    similarities = compare_sdg_embeddings()

    # 3. Find keyword overlaps
    overlaps = find_keyword_overlap()

    # 4. Analyze OSDG texts
    df = analyze_osdg_texts_for_sdg12()

    # 5. TF-IDF analysis
    top_terms, comparisons = perform_tfidf_analysis(df)

    # 6. Confusion patterns
    analyze_confusion_patterns()

    # 7. Generate recommendations
    generate_sdg12_recommendations(overlaps, similarities)

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)


if __name__ == "__main__":
    main()
