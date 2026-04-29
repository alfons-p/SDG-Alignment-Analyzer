#!/usr/bin/env python3
"""Quick grid search for SDG 12 optimal weights with minimal samples.

This is a quick test to find optimal weights for SDG 12 before running full search.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from tqdm import tqdm

from src.hybrid_alignment_engine import HybridAlignmentEngine


def load_sdg12_data(csv_path: Path, n_samples: int = 30) -> pd.DataFrame:
    """Load SDG 12 data from OSDG."""
    df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')
    df = df[(df['sdg'] == 12) & (df['agreement'] >= 0.7)].copy()
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]

    if len(df) > n_samples:
        df = df.sample(n=n_samples, random_state=42)

    return df


def test_weight_combo(
    texts: List[str],
    true_labels: List[int],
    sdg_bert_weight: float,
    st_weight: float,
    model_path: str
) -> Tuple[float, float, float]:
    """Test a specific weight combination."""
    engine = HybridAlignmentEngine(
        model_name=model_path,
        similarity_threshold=0.3,
        use_sdg_bert=True,
        ensemble_mode="weighted",
        sdg_bert_weight=sdg_bert_weight,
        st_weight=st_weight
    )

    predictions = []
    for text in texts:
        try:
            result = engine.align_activity(text, use_ensemble=True)
            pred = 1 if result['top_sdg'] == 12 else 0
            predictions.append(pred)
        except Exception:
            predictions.append(0)

    # Calculate metrics
    tp = sum(1 for yt, yp in zip(true_labels, predictions) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(true_labels, predictions) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(true_labels, predictions) if yt == 1 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return precision, recall, f1


def grid_search_sdg12_quick():
    """Quick grid search for SDG 12."""
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    model_path = "models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509"

    print("="*60)
    print("QUICK GRID SEARCH FOR SDG 12")
    print("="*60)

    # Load data
    df = load_sdg12_data(csv_path, n_samples=30)
    print(f"Loaded {len(df)} SDG 12 texts")

    texts = df['text'].tolist()
    true_labels = [1] * len(texts)

    # Generate weight combinations (5% steps)
    weight_combos = []
    for i in range(21):  # 0% to 100% in 5% steps
        sdg_bert_w = round(i * 0.05, 2)
        st_w = round(1.0 - sdg_bert_w, 2)
        weight_combos.append((sdg_bert_w, st_w))

    print(f"\nTesting {len(weight_combos)} weight combinations...")
    print("-"*60)

    results = []
    for sdg_bert_w, st_w in tqdm(weight_combos, desc="Grid search"):
        precision, recall, f1 = test_weight_combo(
            texts, true_labels, sdg_bert_w, st_w, model_path
        )
        results.append({
            'sdg_bert_weight': sdg_bert_w,
            'st_weight': st_w,
            'precision': precision,
            'recall': recall,
            'f1': f1
        })

    # Find best by F1
    best = max(results, key=lambda x: x['f1'])

    print("\n" + "="*60)
    print("BEST WEIGHTS FOR SDG 12")
    print("="*60)
    print(f"sdgBERT weight: {best['sdg_bert_weight']:.0%}")
    print(f"ST weight:      {best['st_weight']:.0%}")
    print(f"F1 score:       {best['f1']:.2%}")
    print(f"Precision:      {best['precision']:.2%}")
    print(f"Recall:         {best['recall']:.2%}")
    print("="*60)

    # Show top 5
    print("\nTop 5 configurations:")
    top5 = sorted(results, key=lambda x: x['f1'], reverse=True)[:5]
    print(f"{'Rank':<5} {'sdgBERT':<10} {'ST':<10} {'F1':<10} {'Precision':<10} {'Recall':<10}")
    print("-"*60)
    for i, r in enumerate(top5, 1):
        print(f"{i:<5} {r['sdg_bert_weight']:<10.0%} {r['st_weight']:<10.0%} {r['f1']:<10.2%} {r['precision']:<10.2%} {r['recall']:<10.2%}")

    # Save results
    output_path = Path("results/sdg12_grid_search_quick.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump({
            'best': best,
            'all_results': results
        }, f, indent=2)
    print(f"\n✓ Results saved to: {output_path}")

    return best


if __name__ == "__main__":
    grid_search_sdg12_quick()
