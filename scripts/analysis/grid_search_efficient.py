#!/usr/bin/env python3
"""Efficient grid search for SDG-specific ensemble weights.

Pre-loads models once and reuses them across weight combinations.
Uses 5% grid steps for coarse search.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from tqdm import tqdm

from src.hybrid_alignment_engine import HybridAlignmentEngine


@dataclass
class GridResult:
    """Result of a single grid search evaluation."""
    sdg: int
    sdg_bert_weight: float
    st_weight: float
    precision: float
    recall: float
    f1: float


def load_sdg_data(csv_path: Path, target_sdg: int, n_samples: int = 50) -> Tuple[List[str], List[int]]:
    """Load data for a specific SDG."""
    df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')

    # Get positive samples (target SDG)
    pos_df = df[(df['sdg'] == target_sdg) & (df['agreement'] >= 0.7)].copy()
    pos_df = pos_df[pos_df['text'].notna() & (pos_df['text'].str.strip() != '')]

    # Get negative samples (other SDGs)
    neg_df = df[(df['sdg'] != target_sdg) & (df['agreement'] >= 0.7)].copy()
    neg_df = neg_df[neg_df['text'].notna() & (neg_df['text'].str.strip() != '')]

    # Sample
    n_pos = min(len(pos_df), n_samples // 2)
    n_neg = n_samples - n_pos

    if len(pos_df) > n_pos:
        pos_df = pos_df.sample(n=n_pos, random_state=42)
    if len(neg_df) > n_neg:
        neg_df = neg_df.sample(n=n_neg, random_state=42)

    # Combine
    texts = pos_df['text'].tolist() + neg_df['text'].tolist()
    labels = [1] * len(pos_df) + [0] * len(neg_df)

    # Shuffle
    combined = list(zip(texts, labels))
    np.random.seed(42)
    np.random.shuffle(combined)
    texts, labels = zip(*combined) if combined else ([], [])

    return list(texts), list(labels)


def evaluate_weights(
    engine: HybridAlignmentEngine,
    texts: List[str],
    labels: List[int],
    target_sdg: int,
    sdg_bert_weight: float,
    st_weight: float
) -> Tuple[float, float, float]:
    """Evaluate a weight configuration."""
    # Set custom weights for this SDG
    engine.set_sdg_weights(target_sdg, sdg_bert_weight, st_weight)

    predictions = []
    for text in texts:
        try:
            result = engine.align_activity(text, use_ensemble=True)
            pred = 1 if result['top_sdg'] == target_sdg else 0
            predictions.append(pred)
        except Exception:
            predictions.append(0)

    # Calculate metrics
    tp = sum(1 for yt, yp in zip(labels, predictions) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(labels, predictions) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(labels, predictions) if yt == 1 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return precision, recall, f1


def grid_search_sdg(
    engine: HybridAlignmentEngine,
    csv_path: Path,
    target_sdg: int,
    n_samples: int = 50
) -> GridResult:
    """Run grid search for a single SDG."""
    print(f"\n{'='*60}")
    print(f"Grid Search for SDG {target_sdg}")
    print(f"{'='*60}")

    # Load data
    texts, labels = load_sdg_data(csv_path, target_sdg, n_samples)
    print(f"Loaded {len(texts)} samples ({sum(labels)} positive, {len(labels) - sum(labels)} negative)")

    # Generate weight combinations (5% steps)
    weight_combos = [(round(i * 0.05, 2), round(1.0 - i * 0.05, 2)) for i in range(21)]
    print(f"Testing {len(weight_combos)} weight combinations...")

    results = []
    for sdg_bert_w, st_w in tqdm(weight_combos, desc=f"SDG {target_sdg}"):
        precision, recall, f1 = evaluate_weights(
            engine, texts, labels, target_sdg, sdg_bert_w, st_w
        )
        results.append(GridResult(
            sdg=target_sdg,
            sdg_bert_weight=sdg_bert_w,
            st_weight=st_w,
            precision=precision,
            recall=recall,
            f1=f1
        ))

    # Clear custom weights
    engine.clear_custom_weights()

    # Find best by F1
    best = max(results, key=lambda x: x.f1)

    print(f"\nBest weights for SDG {target_sdg}:")
    print(f"  sdgBERT: {best.sdg_bert_weight:.0%}")
    print(f"  ST:      {best.st_weight:.0%}")
    print(f"  F1:      {best.f1:.2%}")
    print(f"  Precision: {best.precision:.2%}")
    print(f"  Recall:  {best.recall:.2%}")

    # Show top 5
    print(f"\nTop 5 configurations:")
    top5 = sorted(results, key=lambda x: x.f1, reverse=True)[:5]
    print(f"{'Rank':<5} {'sdgBERT':<10} {'ST':<10} {'F1':<10} {'Precision':<10} {'Recall':<10}")
    print("-"*60)
    for i, r in enumerate(top5, 1):
        marker = " <- best" if i == 1 else ""
        print(f"{i:<5} {r.sdg_bert_weight:<10.0%} {r.st_weight:<10.0%} {r.f1:<10.2%} {r.precision:<10.2%} {r.recall:<10.2%}{marker}")

    return best, results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Efficient grid search for SDG weights")
    parser.add_argument("--sdgs", nargs="+", type=int, default=[12],
                        help="SDGs to evaluate (default: 12)")
    parser.add_argument("--model-path",
                        default="models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509",
                        help="Path to fine-tuned model")
    parser.add_argument("--csv-path", default="data/external/osdg-community-data-v2024-04-01.csv",
                        help="Path to OSDG data")
    parser.add_argument("--n-samples", type=int, default=50,
                        help="Samples per SDG (default: 50)")

    args = parser.parse_args()

    csv_path = Path(args.csv_path)

    print("="*60)
    print("EFFICIENT GRID SEARCH FOR SDG-SPECIFIC WEIGHTS")
    print("="*60)
    print(f"SDGs to evaluate: {args.sdgs}")
    print(f"Samples per SDG: {args.n_samples}")
    print(f"Weight step: 5%")
    print("-"*60)

    # Initialize engine once
    print("\nInitializing hybrid engine...")
    engine = HybridAlignmentEngine(
        model_name=args.model_path,
        similarity_threshold=0.3,
        use_sdg_bert=True,
        ensemble_mode="weighted"
    )
    print("✓ Engine ready")

    # Run grid search for each SDG
    all_results = {}
    for sdg in args.sdgs:
        best, results = grid_search_sdg(engine, csv_path, sdg, args.n_samples)
        all_results[sdg] = {
            'best': {
                'sdg_bert_weight': best.sdg_bert_weight,
                'st_weight': best.st_weight,
                'precision': best.precision,
                'recall': best.recall,
                'f1': best.f1
            },
            'all_results': [
                {
                    'sdg_bert_weight': r.sdg_bert_weight,
                    'st_weight': r.st_weight,
                    'precision': r.precision,
                    'recall': r.recall,
                    'f1': r.f1
                }
                for r in results
            ]
        }

    # Save results
    output_path = Path("results/grid_search_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n✓ Results saved to: {output_path}")

    # Print summary
    print("\n" + "="*60)
    print("GRID SEARCH SUMMARY")
    print("="*60)
    print(f"{'SDG':<5} {'sdgBERT':<10} {'ST':<10} {'F1':<10} {'Precision':<10} {'Recall':<10}")
    print("-"*60)
    for sdg in args.sdgs:
        best = all_results[sdg]['best']
        print(f"{sdg:<5} {best['sdg_bert_weight']:<10.0%} {best['st_weight']:<10.0%} "
              f"{best['f1']:<10.2%} {best['precision']:<10.2%} {best['recall']:<10.2%}")
    print("="*60)


if __name__ == "__main__":
    main()
