#!/usr/bin/env python3
"""Comprehensive Benchmarking of SDG Alignment Models and Approaches.

This script compares multiple models and approaches using OSDG Community Dataset:
- Base models: all-mpnet-base-v2, all-MiniLM-L6-v2, etc.
- Fine-tuned models: sdg-finetuned, sdg-finetuned-enhanced
- Approaches: Sentence Transformer only, Hybrid (weighted, fallback, single)

Metrics: Accuracy, Precision, Recall, F1-score, F2-score, per-SDG metrics
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from tqdm import tqdm
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, fbeta_score
)
from sentence_transformers import SentenceTransformer

from src.alignment_engine import AlignmentEngine
from src.hybrid_alignment_engine import HybridAlignmentEngine
from src.config import SDG_DEFINITIONS


def load_osdg_data(csv_path: Path, min_agreement: float = 0.7, max_samples: int = 1000) -> pd.DataFrame:
    """Load OSDG data with quality filtering."""
    print(f"Loading OSDG data from {csv_path}...")
    df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')
    print(f"Total records: {len(df)}")

    # Filter by agreement
    df = df[df['agreement'] >= min_agreement].copy()
    print(f"Records with agreement >= {min_agreement}: {len(df)}")

    # Remove empty text
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]
    print(f"Records with valid text: {len(df)}")

    # Filter to valid SDGs (1-17)
    df = df[df['sdg'].isin(range(1, 18))]
    print(f"Records with valid SDG labels: {len(df)}")

    # Sample if needed
    if max_samples and len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)
        print(f"Sampled to {len(df)} records for benchmarking")

    return df


def evaluate_sentence_transformer(
    df: pd.DataFrame,
    model_name: str,
    threshold: float = 0.3
) -> Dict[str, Any]:
    """Evaluate Sentence Transformer only approach."""
    print(f"\nEvaluating ST: {model_name}")
    engine = AlignmentEngine(model_name=model_name, similarity_threshold=threshold)

    predictions = []
    true_labels = []
    scores = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="ST Predictions"):
        text = row['text']
        true_sdg = int(row['sdg'])

        try:
            alignment = engine.align_activity(text)
            pred_sdg = alignment['top_sdg']
            pred_score = alignment['top_score']

            predictions.append(pred_sdg)
            true_labels.append(true_sdg)
            scores.append(pred_score)
        except Exception as e:
            print(f"Error on row {idx}: {e}")
            predictions.append(None)
            true_labels.append(true_sdg)
            scores.append(0)

    # Calculate metrics
    valid_idx = [i for i, p in enumerate(predictions) if p is not None]
    y_true = [true_labels[i] for i in valid_idx]
    y_pred = [predictions[i] for i in valid_idx]

    return calculate_metrics(y_true, y_pred, model_name, "ST Only")


def evaluate_hybrid_approach(
    df: pd.DataFrame,
    model_name: str,
    ensemble_mode: str = "weighted",
    threshold: float = 0.3
) -> Dict[str, Any]:
    """Evaluate Hybrid approach with sdgBERT."""
    print(f"\nEvaluating Hybrid ({ensemble_mode}): {model_name}")
    engine = HybridAlignmentEngine(
        model_name=model_name,
        similarity_threshold=threshold,
        use_sdg_bert=True,
        ensemble_mode=ensemble_mode
    )

    predictions = []
    true_labels = []
    scores = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc=f"Hybrid {ensemble_mode}"):
        text = row['text']
        true_sdg = int(row['sdg'])

        try:
            alignment = engine.align_activity(text, use_ensemble=True)
            pred_sdg = alignment['top_sdg']
            pred_score = alignment['top_score']

            predictions.append(pred_sdg)
            true_labels.append(true_sdg)
            scores.append(pred_score)
        except Exception as e:
            print(f"Error on row {idx}: {e}")
            predictions.append(None)
            true_labels.append(true_sdg)
            scores.append(0)

    # Calculate metrics
    valid_idx = [i for i, p in enumerate(predictions) if p is not None]
    y_true = [true_labels[i] for i in valid_idx]
    y_pred = [predictions[i] for i in valid_idx]

    return calculate_metrics(y_true, y_pred, model_name, f"Hybrid ({ensemble_mode})")


def evaluate_sdg_bert_only(
    df: pd.DataFrame
) -> Dict[str, Any]:
    """Evaluate sdgBERT only approach (no sentence transformer)."""
    from src.sdg_bert_classifier import SDGBERTClassifier

    print(f"\nEvaluating sdgBERT Only")
    classifier = SDGBERTClassifier()

    predictions = []
    true_labels = []
    scores = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="sdgBERT Only"):
        text = row['text']
        true_sdg = int(row['sdg'])

        try:
            result = classifier.predict(text, return_all_scores=True)
            pred_sdg = result['sdg']
            confidence = result['confidence']

            # Handle None predictions (sdgBERT returns None for SDG 17)
            if pred_sdg is None:
                pred_sdg = 17  # Default to 17 if not predicted
                confidence = 0.0

            predictions.append(pred_sdg)
            true_labels.append(true_sdg)
            scores.append(confidence)
        except Exception as e:
            print(f"Error on row {idx}: {e}")
            predictions.append(None)
            true_labels.append(true_sdg)
            scores.append(0)

    # Calculate metrics
    valid_idx = [i for i, p in enumerate(predictions) if p is not None]
    y_true = [true_labels[i] for i in valid_idx]
    y_pred = [predictions[i] for i in valid_idx]

    return calculate_metrics(y_true, y_pred, "sadickam/sdgBERT", "sdgBERT Only")


def calculate_metrics(
    y_true: List[int],
    y_pred: List[int],
    model_name: str,
    approach: str
) -> Dict[str, Any]:
    """Calculate comprehensive metrics."""

    # Basic metrics
    accuracy = accuracy_score(y_true, y_pred)

    # Macro-averaged metrics (treat all SDGs equally)
    precision_macro = precision_score(y_true, y_pred, average='macro', zero_division=0)
    recall_macro = recall_score(y_true, y_pred, average='macro', zero_division=0)
    f1_macro = f1_score(y_true, y_pred, average='macro', zero_division=0)
    f2_macro = fbeta_score(y_true, y_pred, beta=2, average='macro', zero_division=0)

    # Weighted metrics (account for class imbalance)
    precision_weighted = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    recall_weighted = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    f1_weighted = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    f2_weighted = fbeta_score(y_true, y_pred, beta=2, average='weighted', zero_division=0)

    # Per-SDG metrics
    sdg_metrics = {}
    for sdg_num in range(1, 18):
        y_true_sdg = [1 if yt == sdg_num else 0 for yt in y_true]
        y_pred_sdg = [1 if yp == sdg_num else 0 for yp in y_pred]

        tp = sum(1 for yt, yp in zip(y_true_sdg, y_pred_sdg) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(y_true_sdg, y_pred_sdg) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(y_true_sdg, y_pred_sdg) if yt == 1 and yp == 0)

        sdg_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        sdg_recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        sdg_f1 = 2 * sdg_precision * sdg_recall / (sdg_precision + sdg_recall) if (sdg_precision + sdg_recall) > 0 else 0

        sdg_metrics[sdg_num] = {
            'precision': sdg_precision,
            'recall': sdg_recall,
            'f1': sdg_f1,
            'tp': tp,
            'fp': fp,
            'fn': fn
        }

    return {
        'model': model_name,
        'approach': approach,
        'n_samples': len(y_true),
        'accuracy': accuracy,
        'precision_macro': precision_macro,
        'recall_macro': recall_macro,
        'f1_macro': f1_macro,
        'f2_macro': f2_macro,
        'precision_weighted': precision_weighted,
        'recall_weighted': recall_weighted,
        'f1_weighted': f1_weighted,
        'f2_weighted': f2_weighted,
        'sdg_metrics': sdg_metrics,
        'y_true': y_true,
        'y_pred': y_pred
    }


def print_benchmark_report(results: List[Dict[str, Any]]):
    """Print formatted benchmark report."""
    print("\n" + "="*100)
    print("SDG ALIGNMENT MODEL BENCHMARK REPORT")
    print("="*100)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Dataset: OSDG Community Dataset")
    print("="*100)

    # Overall comparison table
    print("\n" + "-"*100)
    print("OVERALL PERFORMANCE COMPARISON")
    print("-"*100)
    print(f"{'Rank':<6} {'Model/Approach':<45} {'Accuracy':<12} {'F1 (Macro)':<12} {'F2 (Macro)':<12}")
    print("-"*100)

    # Sort by F1 macro score
    sorted_results = sorted(results, key=lambda x: x['f1_macro'], reverse=True)

    for rank, result in enumerate(sorted_results, 1):
        name = f"{result['approach']}: {result['model'][:25]}"
        acc = result['accuracy']
        f1 = result['f1_macro']
        f2 = result['f2_macro']
        print(f"{rank:<6} {name:<45} {acc:>10.2%}   {f1:>10.2%}   {f2:>10.2%}")

    # Detailed metrics table
    print("\n" + "-"*100)
    print("DETAILED METRICS")
    print("-"*100)
    print(f"{'Model/Approach':<45} {'Precision':<12} {'Recall':<12} {'F1':<12} {'F2':<12}")
    print("-"*100)

    for result in sorted_results:
        name = f"{result['approach']}: {result['model'][:25]}"
        p = result['precision_macro']
        r = result['recall_macro']
        f1 = result['f1_macro']
        f2 = result['f2_macro']
        print(f"{name:<45} {p:>10.2%}   {r:>10.2%}   {f1:>10.2%}   {f2:>10.2%}")

    # Per-SDG breakdown for top model
    print("\n" + "-"*100)
    print(f"PER-SDG PERFORMANCE: TOP MODEL ({sorted_results[0]['approach']})")
    print("-"*100)
    print(f"{'SDG':<5} {'Name':<35} {'Precision':<12} {'Recall':<12} {'F1':<12}")
    print("-"*100)

    top_result = sorted_results[0]
    for sdg_num in range(1, 18):
        name = SDG_DEFINITIONS[sdg_num]['name'][:33]
        metrics = top_result['sdg_metrics'][sdg_num]
        p = metrics['precision']
        r = metrics['recall']
        f1 = metrics['f1']
        print(f"{sdg_num:<5} {name:<35} {p:>10.2%}   {r:>10.2%}   {f1:>10.2%}")

    print("\n" + "="*100)


def save_benchmark_results(results: List[Dict[str, Any]], output_path: Path):
    """Save benchmark results to JSON and CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare serializable data
    save_data = []
    for result in results:
        data = {
            'model': result['model'],
            'approach': result['approach'],
            'n_samples': result['n_samples'],
            'accuracy': result['accuracy'],
            'precision_macro': result['precision_macro'],
            'recall_macro': result['recall_macro'],
            'f1_macro': result['f1_macro'],
            'f2_macro': result['f2_macro'],
            'precision_weighted': result['precision_weighted'],
            'recall_weighted': result['recall_weighted'],
            'f1_weighted': result['f1_weighted'],
            'f2_weighted': result['f2_weighted'],
            'sdg_metrics': result['sdg_metrics']
        }
        save_data.append(data)

    # Save JSON
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"Results saved to: {json_path}")

    # Save CSV summary with per-SDG metrics
    csv_path = output_path.with_suffix('.csv')

    # Build rows with per-SDG metrics
    rows = []
    for r in results:
        row = {
            'model': r['model'],
            'approach': r['approach'],
            'accuracy': r['accuracy'],
            'precision_macro': r['precision_macro'],
            'recall_macro': r['recall_macro'],
            'f1_macro': r['f1_macro'],
            'f2_macro': r['f2_macro'],
            'precision_weighted': r['precision_weighted'],
            'recall_weighted': r['recall_weighted'],
            'f1_weighted': r['f1_weighted'],
            'f2_weighted': r['f2_weighted']
        }

        # Add per-SDG metrics (SDG 1-17)
        for sdg_num in range(1, 18):
            sdg_data = r['sdg_metrics'].get(sdg_num, {})
            row[f'sdg_{sdg_num}_precision'] = sdg_data.get('precision', 0)
            row[f'sdg_{sdg_num}_recall'] = sdg_data.get('recall', 0)
            row[f'sdg_{sdg_num}_f1'] = sdg_data.get('f1', 0)
            row[f'sdg_{sdg_num}_tp'] = sdg_data.get('tp', 0)
            row[f'sdg_{sdg_num}_fp'] = sdg_data.get('fp', 0)
            row[f'sdg_{sdg_num}_fn'] = sdg_data.get('fn', 0)

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    print(f"CSV summary saved to: {csv_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark SDG alignment models against OSDG data"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=500,
        help="Maximum samples to evaluate (default: 500)"
    )
    parser.add_argument(
        "--min-agreement",
        type=float,
        default=0.7,
        help="Minimum OSDG agreement score"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/benchmark",
        help="Output directory for results"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["all-mpnet-base-v2"],
        help="Models to benchmark"
    )
    parser.add_argument(
        "--approaches",
        nargs="+",
        choices=["st", "sdg_bert_only", "hybrid_weighted", "hybrid_fallback", "hybrid_single"],
        default=["st", "sdg_bert_only", "hybrid_weighted"],
        help="Approaches to benchmark"
    )
    parser.add_argument(
        "--finetuned",
        action="store_true",
        help="Include fine-tuned models"
    )

    args = parser.parse_args()

    # Load OSDG data
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    if not csv_path.exists():
        print(f"Error: OSDG data not found at {csv_path}")
        print("Download from: https://zenodo.org/records/11441197")
        return

    df = load_osdg_data(csv_path, min_agreement=args.min_agreement, max_samples=args.max_samples)

    if len(df) == 0:
        print("No data loaded. Exiting.")
        return

    results = []

    # Define models to test
    models_to_test = args.models.copy()

    # Add fine-tuned models if requested
    if args.finetuned:
        ft_models = [
            "models/sdg-finetuned/sdg-finetuned-20260224_184210",
            "models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509"
        ]
        for ft_model in ft_models:
            if Path(ft_model).exists():
                models_to_test.append(ft_model)
            else:
                print(f"Warning: Fine-tuned model not found: {ft_model}")

    # Calculate total evaluations (sdgBERT only runs once)
    total_evals = 0
    has_sdg_bert_only = "sdg_bert_only" in args.approaches
    other_approaches = [a for a in args.approaches if a != "sdg_bert_only"]
    total_evals = len(models_to_test) * len(other_approaches)
    if has_sdg_bert_only:
        total_evals += 1

    print("\n" + "="*100)
    print(f"BENCHMARKING {len(models_to_test)} MODELS WITH {len(args.approaches)} APPROACHES")
    print(f"Total evaluations: {total_evals}")
    print("="*100)

    # Run benchmarks
    for model in models_to_test:
        for approach in args.approaches:
            try:
                if approach == "st":
                    result = evaluate_sentence_transformer(df, model)
                elif approach == "sdg_bert_only":
                    # sdgBERT only needs to run once (no model parameter)
                    if model == models_to_test[0]:  # Only run once
                        result = evaluate_sdg_bert_only(df)
                    else:
                        continue  # Skip duplicate runs
                elif approach.startswith("hybrid"):
                    mode = approach.split("_")[1]
                    result = evaluate_hybrid_approach(df, model, ensemble_mode=mode)
                else:
                    continue

                results.append(result)

            except Exception as e:
                print(f"Error benchmarking {model} with {approach}: {e}")
                continue

    # Print report
    print_benchmark_report(results)

    # Save results
    output_path = Path(args.output) / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    save_benchmark_results(results, output_path)

    print(f"\nBenchmark complete! Results saved to: {output_path}")


if __name__ == "__main__":
    main()
