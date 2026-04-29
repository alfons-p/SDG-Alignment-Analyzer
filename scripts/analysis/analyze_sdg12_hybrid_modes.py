#!/usr/bin/env python3
"""Quick analysis of SDG 12 performance across hybrid ensemble modes.

This script tests only SDG 12 texts to compare weighted, fallback, and single modes.
"""

import sys
from pathlib import Path
from typing import Dict, List
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from tqdm import tqdm
from sklearn.metrics import precision_score, recall_score, f1_score

from src.hybrid_alignment_engine import HybridAlignmentEngine
from src.config import SDG_DEFINITIONS


def load_sdg12_texts(csv_path: Path, n_samples: int = 50) -> pd.DataFrame:
    """Load only SDG 12 texts from OSDG data."""
    print(f"Loading OSDG data from {csv_path}...")
    df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')

    # Filter for SDG 12 with high agreement
    df = df[(df['sdg'] == 12) & (df['agreement'] >= 0.7)].copy()
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]

    # Sample if too many
    if len(df) > n_samples:
        df = df.sample(n=n_samples, random_state=42)

    print(f"Loaded {len(df)} SDG 12 texts for testing")
    return df


def test_hybrid_mode(df: pd.DataFrame, model_path: str, mode: str) -> Dict:
    """Test a specific hybrid ensemble mode on SDG 12 texts."""
    print(f"\n{'='*80}")
    print(f"Testing Hybrid Mode: {mode.upper()}")
    print(f"{'='*80}")

    engine = HybridAlignmentEngine(
        model_name=model_path,
        similarity_threshold=0.3,
        use_sdg_bert=True,
        ensemble_mode=mode,
        sdg_bert_weight=0.55,
        st_weight=0.45,
        fallback_threshold=0.5
    )

    predictions = []
    true_labels = []
    st_predictions = []
    sdg_bert_predictions = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"Mode: {mode}"):
        text = row['text']
        true_sdg = 12

        try:
            # Get hybrid result
            result = engine.align_activity(text, use_ensemble=True)
            pred_sdg = result['top_sdg']

            # Get individual model predictions if available
            if 'model_predictions' in result:
                st_pred = result['model_predictions']['sentence_transformer']['sdg']
                sdg_bert_pred = result['model_predictions']['sdg_bert']['sdg']
                st_predictions.append(st_pred)
                sdg_bert_predictions.append(sdg_bert_pred)

            predictions.append(pred_sdg)
            true_labels.append(true_sdg)

        except Exception as e:
            print(f"Error on row {idx}: {e}")
            predictions.append(None)
            true_labels.append(true_sdg)

    # Calculate metrics
    valid_idx = [i for i, p in enumerate(predictions) if p is not None]
    y_true = [true_labels[i] for i in valid_idx]
    y_pred = [predictions[i] for i in valid_idx]

    # Binary classification: SDG 12 vs Not SDG 12
    y_true_binary = [1 if y == 12 else 0 for y in y_true]
    y_pred_binary = [1 if y == 12 else 0 for y in y_pred]

    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / len(y_true) if y_true else 0

    # Calculate per-metric
    tp = sum(1 for yt, yp in zip(y_true_binary, y_pred_binary) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true_binary, y_pred_binary) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true_binary, y_pred_binary) if yt == 1 and yp == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Check model agreement
    if st_predictions and sdg_bert_predictions:
        agreements = sum(1 for st, sb in zip(st_predictions, sdg_bert_predictions) if st == sb)
        agreement_rate = agreements / len(st_predictions)
    else:
        agreement_rate = 0

    return {
        'mode': mode,
        'n_samples': len(y_true),
        'correct': correct,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'model_agreement_rate': agreement_rate
    }


def print_comparison(results: List[Dict]):
    """Print comparison table of all modes."""
    print("\n" + "="*80)
    print("SDG 12 HYBRID MODE COMPARISON")
    print("="*80)
    print(f"\n{'Mode':<20} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1':<12}")
    print("-"*80)

    for result in results:
        mode = result['mode']
        acc = result['accuracy']
        prec = result['precision']
        rec = result['recall']
        f1 = result['f1']
        print(f"{mode:<20} {acc:>10.2%}   {prec:>10.2%}   {rec:>10.2%}   {f1:>10.2%}")

    # Detailed breakdown
    print("\n" + "-"*80)
    print("DETAILED BREAKDOWN")
    print("-"*80)
    print(f"{'Mode':<20} {'TP':<8} {'FP':<8} {'FN':<8} {'Model Agree':<15}")
    print("-"*80)

    for result in results:
        mode = result['mode']
        tp = result['tp']
        fp = result['fp']
        fn = result['fn']
        agree = result['model_agreement_rate']
        print(f"{mode:<20} {tp:<8} {fp:<8} {fn:<8} {agree:>13.2%}")

    print("\n" + "="*80)

    # Find best mode
    best_f1 = max(results, key=lambda x: x['f1'])
    best_precision = max(results, key=lambda x: x['precision'])

    print(f"\nBEST F1 SCORE: {best_f1['mode']} ({best_f1['f1']:.2%})")
    print(f"BEST PRECISION: {best_precision['mode']} ({best_precision['precision']:.2%})")


def main():
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    if not csv_path.exists():
        print(f"Error: OSDG data not found at {csv_path}")
        return

    model_path = "models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509"

    # Load SDG 12 texts
    df = load_sdg12_texts(csv_path, n_samples=50)

    if len(df) == 0:
        print("No SDG 12 texts found!")
        return

    print(f"\nTesting {len(df)} SDG 12 texts across 3 hybrid modes...")
    print("This will take approximately 10-15 minutes...")

    # Test each mode
    results = []
    for mode in ['weighted', 'fallback', 'single']:
        result = test_hybrid_mode(df, model_path, mode)
        results.append(result)

    # Print comparison
    print_comparison(results)

    # Save results
    output_path = Path("results/sdg12_hybrid_mode_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
