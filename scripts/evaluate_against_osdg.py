#!/usr/bin/env python3
"""Evaluate current SDG alignment model against OSDG Community Dataset.

This script compares the current model's predictions against crowd-sourced
OSDG labels to measure accuracy and identify areas for improvement.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from tqdm import tqdm

from src.alignment_engine import AlignmentEngine
from src.config import SDG_DEFINITIONS


def load_osdg_data(csv_path: Path, min_agreement: float = 0.7, sample_size: int = None) -> pd.DataFrame:
    """Load OSDG data with quality filtering."""
    print(f"Loading OSDG data from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Total records: {len(df)}")

    # Filter by agreement
    df = df[df['agreement'] >= min_agreement].copy()
    print(f"Records with agreement >= {min_agreement}: {len(df)}")

    # Remove empty text
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]
    print(f"Records with valid text: {len(df)}")

    # Sample if needed
    if sample_size and len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)
        print(f"Sampled to {len(df)} records for evaluation")

    return df


def evaluate_model(
    df: pd.DataFrame,
    model_name: str = "all-mpnet-base-v2",
    threshold: float = 0.3,
    top_n: int = 1
) -> Dict:
    """
    Evaluate model against OSDG labels.

    For each text in OSDG data:
    1. Run model alignment
    2. Compare predicted SDG vs labeled SDG
    3. Track accuracy metrics

    Args:
        df: OSDG DataFrame
        model_name: Sentence transformer model
        threshold: Alignment threshold
        top_n: Consider top N predictions as correct

    Returns:
        Evaluation metrics dictionary
    """
    print(f"\nInitializing model: {model_name}")
    engine = AlignmentEngine(model_name=model_name, similarity_threshold=threshold)

    results = []
    correct_predictions = 0
    total_predictions = 0

    # Track per-SDG metrics
    sdg_metrics = defaultdict(lambda: {
        'true_positives': 0,
        'false_positives': 0,
        'false_negatives': 0,
        'correct': 0,
        'total': 0
    })

    print(f"\nEvaluating {len(df)} texts...")

    for idx, row in tqdm(df.iterrows(), total=len(df)):
        text = row['text']
        true_sdg = int(row['sdg'])
        agreement = row['agreement']

        try:
            # Get model prediction
            alignment = engine.align_activity(text, return_top_n=top_n)
            predicted_sdg = alignment['top_sdg']
            predicted_score = alignment['top_score']
            top_sdgs = [s['sdg'] for s in alignment.get('top_sdgs', [])]

            # Check if correct
            is_correct = predicted_sdg == true_sdg
            is_in_top_n = true_sdg in top_sdgs[:top_n] if top_n > 1 else is_correct

            if is_in_top_n:
                correct_predictions += 1
            total_predictions += 1

            # Update per-SDG metrics
            sdg_metrics[true_sdg]['total'] += 1
            if is_in_top_n:
                sdg_metrics[true_sdg]['correct'] += 1

            # Store result
            results.append({
                'text_id': row.get('text_id', idx),
                'true_sdg': true_sdg,
                'predicted_sdg': predicted_sdg,
                'predicted_score': predicted_score,
                'correct': is_in_top_n,
                'agreement': agreement,
                'text_preview': text[:100] + "..." if len(text) > 100 else text
            })

        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            continue

    # Calculate overall accuracy
    accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0

    # Calculate per-SDG accuracy
    sdg_accuracies = {}
    for sdg_num in range(1, 18):
        metrics = sdg_metrics[sdg_num]
        sdg_accuracies[sdg_num] = {
            'accuracy': metrics['correct'] / metrics['total'] if metrics['total'] > 0 else 0,
            'correct': metrics['correct'],
            'total': metrics['total']
        }

    return {
        'model': model_name,
        'threshold': threshold,
        'top_n': top_n,
        'total_evaluated': total_predictions,
        'correct_predictions': correct_predictions,
        'overall_accuracy': accuracy,
        'sdg_accuracies': sdg_accuracies,
        'results_df': pd.DataFrame(results)
    }


def analyze_errors(results_df: pd.DataFrame, n_samples: int = 5) -> Dict:
    """Analyze common misclassifications."""

    errors_df = results_df[results_df['correct'] == False]

    # Most commonly confused SDG pairs
    confusion_pairs = errors_df.groupby(['true_sdg', 'predicted_sdg']).size().reset_index(name='count')
    confusion_pairs = confusion_pairs.sort_values('count', ascending=False).head(10)

    # SDGs with lowest accuracy
    sdg_stats = results_df.groupby('true_sdg').agg({
        'correct': ['count', 'sum']
    }).reset_index()
    sdg_stats.columns = ['sdg', 'total', 'correct']
    sdg_stats['accuracy'] = sdg_stats['correct'] / sdg_stats['total']
    sdg_stats = sdg_stats.sort_values('accuracy')

    return {
        'confusion_pairs': confusion_pairs,
        'lowest_accuracy_sdgs': sdg_stats.head(n_samples),
        'error_samples': errors_df.head(n_samples)
    }


def print_report(evaluation: Dict, error_analysis: Dict):
    """Print formatted evaluation report."""

    print("\n" + "="*70)
    print("OSDG EVALUATION REPORT")
    print("="*70)

    print(f"\nModel: {evaluation['model']}")
    print(f"Threshold: {evaluation['threshold']}")
    print(f"Top-N Considered: {evaluation['top_n']}")

    print(f"\nOverall Accuracy: {evaluation['overall_accuracy']:.2%}")
    print(f"Correct: {evaluation['correct_predictions']} / {evaluation['total_evaluated']}")

    print("\n" + "-"*70)
    print("PER-SDG ACCURACY")
    print("-"*70)
    print(f"{'SDG':<5} {'Name':<40} {'Accuracy':<10} {'Count':<10}")
    print("-"*70)

    for sdg_num in range(1, 18):
        acc_data = evaluation['sdg_accuracies'][sdg_num]
        name = SDG_DEFINITIONS[sdg_num]['name'][:37]
        accuracy = acc_data['accuracy']
        total = acc_data['total']
        correct = acc_data['correct']

        if total > 0:
            print(f"{sdg_num:<5} {name:<40} {accuracy:>8.1%}   {correct:>3}/{total:<3}")

    print("\n" + "-"*70)
    print("SDGs WITH LOWEST ACCURACY")
    print("-"*70)

    for _, row in error_analysis['lowest_accuracy_sdgs'].iterrows():
        sdg_num = int(row['sdg'])
        name = SDG_DEFINITIONS[sdg_num]['name']
        print(f"SDG {sdg_num}: {name} - {row['accuracy']:.1%} ({int(row['correct'])}/{int(row['total'])})")

    print("\n" + "-"*70)
    print("MOST COMMON MISCLASSIFICATIONS")
    print("-"*70)
    print(f"{'True SDG':<20} → {'Predicted SDG':<20} {'Count':<10}")
    print("-"*70)

    for _, row in error_analysis['confusion_pairs'].iterrows():
        true_sdg = int(row['true_sdg'])
        pred_sdg = int(row['predicted_sdg'])
        true_name = SDG_DEFINITIONS[true_sdg]['name'][:17]
        pred_name = SDG_DEFINITIONS[pred_sdg]['name'][:17]
        count = row['count']

        print(f"SDG {true_sdg} ({true_name}) → SDG {pred_sdg} ({pred_name})   {count}")

    print("\n" + "="*70)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate SDG alignment model against OSDG Community Dataset"
    )
    parser.add_argument(
        "--model",
        default="all-mpnet-base-v2",
        help="Model to evaluate (default: all-mpnet-base-v2)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Similarity threshold"
    )
    parser.add_argument(
        "--min-agreement",
        type=float,
        default=0.7,
        help="Minimum OSDG agreement score"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=1000,
        help="Number of samples to evaluate (default: 1000)"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=1,
        help="Consider top N predictions as correct (default: 1)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file"
    )

    args = parser.parse_args()

    # Load OSDG data
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    if not csv_path.exists():
        print(f"Error: OSDG data not found at {csv_path}")
        print("Download it from: https://zenodo.org/records/11441197")
        return

    df = load_osdg_data(csv_path, min_agreement=args.min_agreement, sample_size=args.sample_size)

    # Run evaluation
    evaluation = evaluate_model(
        df,
        model_name=args.model,
        threshold=args.threshold,
        top_n=args.top_n
    )

    # Analyze errors
    error_analysis = analyze_errors(evaluation['results_df'])

    # Print report
    print_report(evaluation, error_analysis)

    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        save_data = {
            'model': evaluation['model'],
            'threshold': evaluation['threshold'],
            'overall_accuracy': evaluation['overall_accuracy'],
            'sdg_accuracies': evaluation['sdg_accuracies'],
            'confusion_pairs': error_analysis['confusion_pairs'].to_dict('records')
        }

        with open(output_path, 'w') as f:
            json.dump(save_data, f, indent=2)

        print(f"\nResults saved to: {output_path}")

    # Save detailed results CSV
    results_csv = Path("data/results/osdg_evaluation_results.csv")
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    evaluation['results_df'].to_csv(results_csv, index=False)
    print(f"Detailed results saved to: {results_csv}")


if __name__ == "__main__":
    main()
