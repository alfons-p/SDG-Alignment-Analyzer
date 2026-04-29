#!/usr/bin/env python3
"""Optimize threshold for SDG alignment using Sentence Transformer.

This script finds the optimal similarity threshold that maximizes F1 score
for SDG alignment using the ST (Sentence Transformer) model.

Usage:
    python scripts/analysis/optimize_threshold.py --sdg 12
    python scripts/analysis/optimize_threshold.py --sdg all
    python scripts/analysis/optimize_threshold.py --sdg combined
"""

import sys
import math
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import json
import argparse
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
from tqdm import tqdm
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
from sklearn.preprocessing import StandardScaler

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier
from src.config import Config
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT


# Default output directory for JSON results
DEFAULT_OUTPUT_DIR = Path("results/threshold_optimization")


class ThresholdResult:
    """Result for a single threshold evaluation."""
    def __init__(self, threshold: float, precision: float, recall: float,
                 f1: float, accuracy: float, num_positives: int):
        self.threshold = threshold
        self.precision = precision
        self.recall = recall
        self.f1 = f1
        self.accuracy = accuracy
        self.num_positives = num_positives

    def __repr__(self):
        return (f"ThresholdResult(threshold={self.threshold:.2f}, "
                f"F1={self.f1:.3f}, P={self.precision:.3f}, R={self.recall:.3f})")


def load_osdg_data(csv_path: Path, target_sdg: int = None, agreement_threshold: float = 0.7) -> dict:
    """Load OSDG data and prepare for SDG classification.

    Args:
        csv_path: Path to OSDG CSV file
        target_sdg: Target SDG number (1-17), or None for 'combined' mode
        agreement_threshold: Minimum agreement threshold

    Returns:
        Dictionary with data based on mode
    """
    import pandas as pd

    print(f"Loading OSDG data from {csv_path}...")
    df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')

    # Filter by agreement
    df = df[df['agreement'] >= agreement_threshold].copy()
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]

    print(f"Loaded {len(df)} records with agreement >= {agreement_threshold}")

    # Show counts per SDG
    sdg_counts = df['sdg'].value_counts().sort_index()
    print(f"Samples per SDG: {dict(sdg_counts)}")

    if target_sdg is not None:
        # Single SDG mode: target_sdg = positive, all others = negative
        pos_df = df[df['sdg'] == target_sdg].copy()
        neg_df = df[df['sdg'] != target_sdg].copy()

        print(f"SDG {target_sdg} positive samples: {len(pos_df)}")
        print(f"Negative samples (other SDGs): {len(neg_df)}")

        # Check for insufficient samples
        if len(pos_df) == 0:
            print(f"\n⚠️  WARNING: No samples found for SDG {target_sdg}!")
            print(f"   This SDG cannot be optimized. Using a default threshold.")
            print(f"   Note: OSDG dataset may not contain all 17 SDGs.")

        return {
            'positive_texts': pos_df['text'].tolist(),
            'negative_texts': neg_df['text'].tolist(),
            'all_texts': df['text'].tolist(),
            'all_labels': df['sdg'].tolist()
        }
    else:
        # Combined mode: return all data
        return {
            'positive_texts': [],
            'negative_texts': [],
            'all_texts': df['text'].tolist(),
            'all_labels': df['sdg'].tolist()
        }


def get_balanced_samples(
    positive_texts: List[str],
    negative_texts: List[str],
    n_samples: int = 100,
    random_state: int = 42
) -> Tuple[List[str], List[int]]:
    """Get balanced positive/negative samples.

    Args:
        positive_texts: List of texts labeled as target SDG
        negative_texts: List of texts not labeled as target SDG
        n_samples: Total number of samples (split evenly)
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (texts, labels)
    """
    np.random.seed(random_state)

    n_pos = min(len(positive_texts), n_samples // 2)
    n_neg = min(len(negative_texts), n_samples // 2)

    # Sample
    pos_sample = np.random.choice(positive_texts, size=n_pos, replace=False).tolist()
    neg_sample = np.random.choice(negative_texts, size=n_neg, replace=False).tolist()

    texts = pos_sample + neg_sample
    labels = [1] * n_pos + [0] * n_neg

    # Shuffle
    combined = list(zip(texts, labels))
    np.random.shuffle(combined)
    texts, labels = zip(*combined)

    return list(texts), list(labels)


def get_combined_samples(
    all_texts: List[str],
    all_labels: List[int],
    n_samples: int = 100,
    random_state: int = 42
) -> Tuple[List[str], List[int]]:
    """Get balanced samples for multi-class SDG classification.

    In combined mode, we sample equally from all SDGs and create
    binary labels for each SDG during evaluation.

    Args:
        all_texts: List of all texts
        all_labels: List of SDG labels (1-17)
        n_samples: Total number of samples (distributed across SDGs)
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (texts, labels)
    """
    import pandas as pd

    np.random.seed(random_state)

    df = pd.DataFrame({'text': all_texts, 'sdg': all_labels})

    # Sample equally from each SDG
    n_per_sdg = n_samples // 17  # Distribute evenly across 17 SDGs

    sampled_texts = []
    sampled_labels = []

    for sdg in range(1, 18):
        sdg_df = df[df['sdg'] == sdg]
        n = min(len(sdg_df), n_per_sdg)
        if n > 0:
            samples = sdg_df.sample(n=n, random_state=random_state)
            sampled_texts.extend(samples['text'].tolist())
            sampled_labels.extend(samples['sdg'].tolist())

    # Shuffle
    combined = list(zip(sampled_texts, sampled_labels))
    np.random.shuffle(combined)
    sampled_texts, sampled_labels = zip(*combined)

    print(f"Combined mode: {len(sampled_texts)} samples across {len(set(sampled_labels))} SDGs")

    return list(sampled_texts), list(sampled_labels)

    texts = pos_sample + neg_sample
    labels = [1] * n_pos + [0] * n_neg

    # Shuffle
    combined = list(zip(texts, labels))
    np.random.shuffle(combined)
    texts, labels = zip(*combined)

    return list(texts), list(labels)


def evaluate_threshold(
    threshold: float,
    texts: List[str],
    labels: List[int],
    engine: AlignmentEngine,
    target_sdg: int = 12
) -> ThresholdResult:
    """Evaluate a specific threshold for SDG 12.

    Args:
        threshold: Similarity threshold to test
        texts: List of activity texts
        labels: Ground truth labels (1 = SDG 12, 0 = not SDG 12)
        engine: Alignment engine
        target_sdg: Target SDG number (default 12)

    Returns:
        ThresholdResult with metrics
    """
    predictions = []

    for text in texts:
        try:
            result = engine.align_activity(text, use_cache=False)

            # Get score for the target SDG
            sdg_score = result['sdg_scores'][target_sdg]['score']

            # Predict positive if score >= threshold
            prediction = 1 if sdg_score >= threshold else 0
            predictions.append(prediction)

        except Exception as e:
            # Default to negative on error
            predictions.append(0)

    if len(predictions) == 0:
        return ThresholdResult(threshold, 0, 0, 0, 0, 0)

    # Calculate metrics
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='binary', zero_division=0
    )
    accuracy = accuracy_score(labels, predictions)

    return ThresholdResult(
        threshold=threshold,
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
        num_positives=sum(predictions)
    )


def evaluate_threshold_combined(
    threshold: float,
    texts: List[str],
    true_sdgs: List[int],
    engine: AlignmentEngine
) -> ThresholdResult:
    """Evaluate threshold in combined/multi-label mode.

    For each text, we predict all SDGs with score >= threshold.
    Compare predicted SDGs vs true SDGs using multi-label metrics.

    Args:
        threshold: Similarity threshold to test
        texts: List of activity texts
        true_sdgs: List of true SDG labels (one per text)
        engine: Alignment engine

    Returns:
        ThresholdResult with macro-averaged metrics
    """
    from sklearn.metrics import f1_score, precision_score, recall_score

    all_predictions = []
    all_true = []

    for i, text in enumerate(texts):
        try:
            result = engine.align_activity(text, use_cache=False)

            # Get predicted SDGs (those with score >= threshold)
            predicted = set()
            for sdg in range(1, 18):
                if result['sdg_scores'][sdg]['score'] >= threshold:
                    predicted.add(sdg)

            # True SDGs
            true = {true_sdgs[i]}

            all_predictions.append(predicted)
            all_true.append(true)

        except Exception:
            all_predictions.append(set())
            all_true.append({true_sdgs[i]})

    if len(all_predictions) == 0:
        return ThresholdResult(threshold, 0, 0, 0, 0, 0)

    # Convert to binary arrays for sklearn
    n_samples = len(all_predictions)
    n_labels = 17

    y_true = np.zeros((n_samples, n_labels), dtype=int)
    y_pred = np.zeros((n_samples, n_labels), dtype=int)

    for i, (true_set, pred_set) in enumerate(zip(all_true, all_predictions)):
        for sdg in true_set:
            if 1 <= sdg <= 17:
                y_true[i, sdg - 1] = 1
        for sdg in pred_set:
            if 1 <= sdg <= 17:
                y_pred[i, sdg - 1] = 1

    # Calculate macro metrics
    precision = precision_score(y_true, y_pred, average='macro', zero_division=0)
    recall = recall_score(y_true, y_pred, average='macro', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)

    # Accuracy: exact match
    accuracy = np.mean(np.all(y_true == y_pred, axis=1))

    num_positives = np.sum(y_pred)

    return ThresholdResult(
        threshold=threshold,
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
        num_positives=num_positives
    )


def get_score_range(
    texts: List[str],
    target_sdg: int = 12
) -> Tuple[float, float, dict]:
    """Get the min and max SDG scores from actual computations.

    Args:
        texts: List of activity texts
        target_sdg: Target SDG number

    Returns:
        Tuple of (min_score, max_score, stats_dict)
    """
    print(f"\nComputing SDG {target_sdg} score distribution...")
    engine = AlignmentEngine(similarity_threshold=0.0)

    scores = []
    for text in tqdm(texts, desc="Computing ST scores"):
        try:
            result = engine.align_activity(text, use_cache=False)
            score = result['sdg_scores'][target_sdg]['score']
            scores.append(score)
        except Exception:
            pass

    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 1.0

    st_mean = np.mean(scores)
    st_std = np.std(scores)

    print(f"ST Score range: {min_score:.3f} to {max_score:.3f}")
    print(f"  Mean: {st_mean:.3f}, Median: {np.median(scores):.3f}, Std: {st_std:.3f}")

    # Compute ST z-scores using StandardScaler
    if len(scores) > 1:
        st_scaler = StandardScaler()
        st_scores_z = st_scaler.fit_transform(np.array(scores).reshape(-1, 1)).flatten()
        print(f"ST z-score range: {st_scores_z.min():.3f} to {st_scores_z.max():.3f}")
        print(f"  Mean: {st_scores_z.mean():.3f}, Std: {st_scores_z.std():.3f}")

    # Also compute sdgBERT scores for reference (but don't use for optimization)
    bert_mean = None
    bert_std = None
    bert_scores = []
    print(f"\nComputing SDG {target_sdg} sdgBERT score distribution...")
    try:
        sdg_bert = SDGBERTClassifier()

        for text in tqdm(texts, desc="Computing sdgBERT scores"):
            try:
                result = sdg_bert.predict(text, return_all_scores=True)
                score = result['all_scores'].get(target_sdg, 0.0)
                bert_scores.append(score)
            except Exception:
                pass

        if bert_scores:
            bert_mean = np.mean(bert_scores)
            bert_std = np.std(bert_scores)
            print(f"sdgBERT Score range: {min(bert_scores):.3f} to {max(bert_scores):.3f}")
            print(f"  Mean: {bert_mean:.3f}, Median: {np.median(bert_scores):.3f}, Std: {bert_std:.3f}")

            # Compute sdgBERT z-scores using StandardScaler
            if len(bert_scores) > 1:
                bert_scaler = StandardScaler()
                bert_scores_z = bert_scaler.fit_transform(np.array(bert_scores).reshape(-1, 1)).flatten()
                print(f"sdgBERT z-score range: {bert_scores_z.min():.3f} to {bert_scores_z.max():.3f}")
                print(f"  Mean: {bert_scores_z.mean():.3f}, Std: {bert_scores_z.std():.3f}")
    except Exception as e:
        print(f"sdgBERT not available: {e}")

    stats = {
        'st_mean': st_mean,
        'st_std': st_std,
        'bert_mean': bert_mean,
        'bert_std': bert_std
    }

    return min_score, max_score, stats, bert_scores


def optimize_threshold(
    texts: List[str],
    labels: List[int],
    thresholds: List[float],
    target_sdg: int = 12,
    stats: dict = None,
    bert_scores: List[float] = None
) -> Tuple[float, List[ThresholdResult], dict]:
    """Find optimal threshold for SDG alignment.

    Args:
        texts: List of activity texts
        labels: Ground truth labels
        thresholds: List of thresholds to test
        target_sdg: Target SDG number
        stats: Statistics dict with st_mean, st_std, bert_mean, bert_std
        bert_scores: List of sdgBERT scores for each text

    Returns:
        Tuple of (best_threshold, all_results, threshold_info)
    """
    # Create ST-only engine
    print(f"\nInitializing Alignment Engine (ST-only mode)...")
    engine = AlignmentEngine(similarity_threshold=0.1)

    # Test each threshold
    results = []
    for thresh in tqdm(thresholds, desc="Testing thresholds"):
        result = evaluate_threshold(thresh, texts, labels, engine, target_sdg)
        results.append(result)

    # Find best by F1
    best = max(results, key=lambda x: x.f1)

    # Compute sdgBERT threshold from ST threshold
    threshold_info = {}
    print(f"DEBUG: stats={stats is not None}, bert_scores={bert_scores is not None}")
    if stats and bert_scores:
        st_std = stats.get('st_std')
        bert_std = stats.get('bert_std')
        bert_mean = stats.get('bert_mean')
        print(f"DEBUG: st_std={st_std}, bert_std={bert_std}, bert_mean={bert_mean}")
        if st_std and st_std > 0 and bert_std and bert_std > 0 and bert_mean is not None:
            st_threshold = best.threshold
            st_mean = stats['st_mean']

            # Convert ST threshold to z-score
            threshold_z = (st_threshold - st_mean) / st_std

            # Convert z-score to sdgBERT threshold
            sdgbert_threshold = threshold_z * bert_std + bert_mean

            # Compute F1 metrics using sdgBERT threshold
            predictions_bert = [1 if score >= sdgbert_threshold else 0 for score in bert_scores]
            precision_bert, recall_bert, f1_bert, _ = precision_recall_fscore_support(
                labels, predictions_bert, average='binary', zero_division=0
            )
            accuracy_bert = accuracy_score(labels, predictions_bert)

            threshold_info = {
                'st_threshold': st_threshold,
                'threshold_z': threshold_z,
                'sdgbert_threshold': sdgbert_threshold,
                'sdgbert_f1': f1_bert,
                'sdgbert_precision': precision_bert,
                'sdgbert_recall': recall_bert,
                'sdgbert_accuracy': accuracy_bert,
                'st_precision': best.precision
            }

            # Compute ST and sdgBERT weights based on precision ratio
            st_precision = best.precision
            total_precision = st_precision + precision_bert
            if total_precision > 0:
                st_weight = st_precision / total_precision
                sdgbert_weight = precision_bert / total_precision
            else:
                st_weight = 0.5
                sdgbert_weight = 0.5

            threshold_info['st_weight'] = st_weight
            threshold_info['sdgbert_weight'] = sdgbert_weight
            threshold_info['hybrid_threshold'] = (st_weight * st_threshold) + (sdgbert_weight * sdgbert_threshold)

            print(f"\nDEBUG: Inside threshold conversion block!")

            print(f"\n{'='*50}")
            print("THRESHOLD CONVERSION")
            print(f"{'='*50}")
            print(f"ST optimal threshold:    {st_threshold:.3f}")
            print(f"ST mean:                 {st_mean:.3f}")
            print(f"ST std:                  {st_std:.3f}")
            print(f"Threshold z-score:        {threshold_z:.3f}")
            print(f"sdgBERT threshold:       {sdgbert_threshold:.3f}")
            print(f"sdgBERT mean:            {bert_mean:.3f}")
            print(f"sdgBERT std:             {bert_std:.3f}")
            print(f"\nsdgBERT Threshold Metrics:")
            print(f"  F1:       {f1_bert:.3f}")
            print(f"  Precision:{precision_bert:.3f}")
            print(f"  Recall:   {recall_bert:.3f}")
            print(f"  Accuracy: {accuracy_bert:.3f}")
            print(f"\nPrecision-based Ensemble Weights:")
            print(f"  ST weight:       {st_weight:.3f}")
            print(f"  sdgBERT weight:  {sdgbert_weight:.3f}")
            print(f"  Hybrid threshold: {(st_weight * st_threshold) + (sdgbert_weight * sdgbert_threshold):.3f}")

    return best.threshold, results, threshold_info


def optimize_threshold_with_cv(
    texts: List[str],
    labels: List[int],
    thresholds: List[float],
    n_folds: int = 5,
    target_sdg: int = 12,
    stats: dict = None,
    bert_scores: List[float] = None
) -> Tuple[float, List[ThresholdResult], List[dict]]:
    """Find optimal threshold using k-fold cross-validation.

    Args:
        texts: List of activity texts
        labels: Ground truth labels
        thresholds: List of thresholds to test
        n_folds: Number of folds for cross-validation
        target_sdg: Target SDG number
        stats: Statistics dict (not used in CV, computed at end)
        bert_scores: BERT scores (not used in CV, computed at end)

    Returns:
        Tuple of (average_best_threshold, all_fold_results, fold_details)
    """
    from sklearn.model_selection import KFold

    print(f"\nRunning {n_folds}-fold cross-validation...")
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)

    fold_best_thresholds = []
    fold_details = []

    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(texts)):
        fold_texts = [texts[i] for i in train_idx]
        fold_labels = [labels[i] for i in train_idx]

        print(f"\n--- Fold {fold_idx + 1}/{n_folds} ---")
        print(f"  Training samples: {len(fold_texts)} ({sum(fold_labels)} positive)")

        # Find best threshold for this fold (skip stats/bert_scores in CV mode)
        best_thresh, fold_results, _ = optimize_threshold(
            fold_texts, fold_labels, thresholds, target_sdg
        )
        fold_best_thresholds.append(best_thresh)

        # Get best result for this fold
        best_result = next(r for r in fold_results if r.threshold == best_thresh)
        fold_details.append({
            'fold': fold_idx + 1,
            'best_threshold': best_thresh,
            'f1': best_result.f1,
            'precision': best_result.precision,
            'recall': best_result.recall,
            'accuracy': best_result.accuracy,
            'train_samples': len(fold_texts),
            'val_samples': len(val_idx)
        })

        print(f"  Fold {fold_idx + 1} best threshold: {best_thresh:.2f} (F1: {best_result.f1:.3f})")

    # Calculate average threshold
    avg_threshold = np.mean(fold_best_thresholds)
    std_threshold = np.std(fold_best_thresholds)

    print(f"\n{'=' * 70}")
    print("CROSS-VALIDATION RESULTS")
    print(f"{'=' * 70}")
    print(f"Per-fold thresholds: {[f'{t:.2f}' for t in fold_best_thresholds]}")
    print(f"Average threshold: {avg_threshold:.2f} (±{std_threshold:.2f})")
    print(f"Mean F1: {np.mean([d['f1'] for d in fold_details]):.3f}")
    print(f"Mean Precision: {np.mean([d['precision'] for d in fold_details]):.3f}")
    print(f"Mean Recall: {np.mean([d['recall'] for d in fold_details]):.3f}")

    return avg_threshold, [], fold_details
    """Find optimal threshold for SDG alignment.

    Args:
        texts: List of activity texts
        labels: Ground truth labels
        thresholds: List of thresholds to test
        target_sdg: Target SDG number

    Returns:
        Tuple of (best_threshold, all_results)
    """
    # Create ST-only engine
    print(f"\nInitializing Alignment Engine (ST-only mode)...")
    engine = AlignmentEngine(similarity_threshold=0.1)

    # Test each threshold
    results = []
    for thresh in tqdm(thresholds, desc="Testing thresholds"):
        result = evaluate_threshold(thresh, texts, labels, engine, target_sdg)
        results.append(result)

    # Find best by F1
    best = max(results, key=lambda x: x.f1)

    return best.threshold, results


def print_results(results: List[ThresholdResult], top_n: int = 10):
    """Print threshold optimization results."""
    # Sort by F1
    sorted_results = sorted(results, key=lambda x: x.f1, reverse=True)

    print("\n" + "=" * 70)
    print(f"TOP {top_n} THRESHOLDS BY F1 SCORE")
    print("=" * 70)
    print(f"{'Threshold':<12} {'F1':<10} {'Precision':<12} {'Recall':<10} {'Accuracy':<10}")
    print("-" * 70)

    for r in sorted_results[:top_n]:
        print(f"{r.threshold:<12.2f} {r.f1:<10.3f} {r.precision:<12.3f} "
              f"{r.recall:<10.3f} {r.accuracy:<10.3f}")


def main():
    parser = argparse.ArgumentParser(description="Optimize threshold for SDG alignment (ST mode)")
    parser.add_argument("--csv-path",
                        default="data/external/osdg-community-data-v2024-04-01.csv",
                        help="Path to OSDG data")
    parser.add_argument("--sdg", type=str, default="12",
                        help="Target SDG: number (1-17), comma-separated (2,5), 'all', or 'combined'")
    parser.add_argument("--n-samples", type=int, default=100,
                        help="Total samples per SDG (for 'all' mode) or total (for single/combined)")
    parser.add_argument("--agreement", type=float, default=0.7,
                        help="Minimum agreement threshold for OSDG")
    parser.add_argument("--step", type=float, default=0.05,
                        help="Threshold step size")
    parser.add_argument("--cv", type=int, default=None,
                        help="Number of folds for cross-validation (minimum 2, e.g., --cv 5)")
    parser.add_argument("--output", type=str, default=None,
                        help=f"Output JSON path (default: {DEFAULT_OUTPUT_DIR}/<timestamp>_<sdg>.json)")
    parser.add_argument("--no-output", action="store_true",
                        help="Disable JSON output")
    parser.add_argument("--pct-samples", type=float, default=None,
                        help="Sample percentage (0.0-1.0) instead of --n-samples. "
                             "Single/multiple/all modes: pct * 2 * min(positive, negative) total. "
                             "Combined mode: pct * total dataset size.")

    args = parser.parse_args()

    # Generate default output path if not specified and not disabled
    if args.output is None and not args.no_output:
        # Create default output directory
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sdg_input = args.sdg.lower()
        if sdg_input in ["all", "combined"]:
            sdg_part = sdg_input
        elif "," in args.sdg:
            # Multiple SDGs: "2,5" -> "sdg2_5"
            sdg_part = "_".join(f"sdg{s.strip()}" for s in args.sdg.split(","))
        else:
            sdg_part = f"sdg{args.sdg}"
        args.output = str(DEFAULT_OUTPUT_DIR / f"{timestamp}_{sdg_part}.json")

    # Parse SDG argument
    target_sdg = None
    target_sdgs = None  # For multiple SDGs
    mode = "single"

    sdg_input = args.sdg.lower()

    if sdg_input == "all":
        mode = "all"
        target_sdg = None
    elif sdg_input == "combined":
        mode = "combined"
        target_sdg = None
    elif "," in args.sdg:
        # Multiple SDGs: e.g., "2,5" or "1,3,12"
        mode = "multiple"
        target_sdgs = []
        for part in args.sdg.split(","):
            try:
                sdg_num = int(part.strip())
                if sdg_num < 1 or sdg_num > 17:
                    raise ValueError(f"Invalid SDG number: {sdg_num}")
                target_sdgs.append(sdg_num)
            except ValueError as e:
                print(f"Error: Invalid SDG number in '{args.sdg}': {e}")
                sys.exit(1)
        if not target_sdgs:
            print(f"Error: No valid SDGs in '{args.sdg}'")
            sys.exit(1)
    else:
        try:
            target_sdg = int(args.sdg)
            if target_sdg < 1 or target_sdg > 17:
                raise ValueError("SDG must be between 1 and 17")
            mode = "single"
        except ValueError:
            print(f"Error: --sdg must be a number (1-17), comma-separated (2,5), 'all', or 'combined', got: {args.sdg}")
            sys.exit(1)

    # For 'combined' mode, use minimum 100 samples
    n_samples = args.n_samples
    if mode == "combined" and n_samples < 100:
        n_samples = 100
        print(f"Using minimum 100 samples for combined mode: {n_samples}")

    # Load data
    osdg_data = load_osdg_data(
        Path(args.csv_path),
        target_sdg=target_sdg,
        agreement_threshold=args.agreement
    )

    # Convert --pct-samples to absolute number if specified
    if args.pct_samples is not None:
        if mode == "single" or mode == "multiple":
            # Percentage of 2 * min(positive, negative) for balanced sampling
            if mode == "single":
                n_pos = sum(1 for l in osdg_data['all_labels'] if l == target_sdg)
                n_neg = sum(1 for l in osdg_data['all_labels'] if l != target_sdg)
            else:
                # Will be computed per-SDG below
                pass
            min_class = min(n_pos, n_neg)
            n_samples = int(args.pct_samples * 2 * min_class)
            print(f"\n--pct-samples={args.pct_samples}: using {n_samples} samples "
                  f"({min_class} positive, {min_class} negative)")
        elif mode == "all":
            # Percentage of 2 * min class across all SDGs for balanced sampling
            sdg_counts = pd.Series(osdg_data['all_labels']).value_counts()
            min_class = min(sdg_counts.values)
            n_samples = int(args.pct_samples * 2 * min_class)
            print(f"\n--pct-samples={args.pct_samples}: using {n_samples} samples per SDG "
                  f"(min class size: {min_class})")
        elif mode == "combined":
            n_samples = int(args.pct_samples * len(osdg_data['all_texts']))
            print(f"\n--pct-samples={args.pct_samples}: using {n_samples} samples "
                  f"({args.pct_samples * 100:.0f}% of {len(osdg_data['all_texts'])} total)")

    if mode == "single":
        # Single SDG mode
        texts, labels = get_balanced_samples(
            osdg_data['positive_texts'],
            osdg_data['negative_texts'],
            n_samples=n_samples
        )
        print(f"\nUsing {len(texts)} samples ({sum(labels)} positive, {len(labels) - sum(labels)} negative)")

        # Check for insufficient positive samples
        if sum(labels) == 0:
            # Get defaults from config
            config = Config()
            st_default = config.get_similarity_threshold('st', sdg=target_sdg)
            hybrid_default = config.get_similarity_threshold('hybrid', sdg=target_sdg)

            print("\n" + "=" * 70)
            print("⚠️  CANNOT OPTIMIZE - NO POSITIVE SAMPLES")
            print("=" * 70)
            print(f"SDG {target_sdg} has no samples in the OSDG dataset.")
            print("This is common for SDG 17 (Partnerships) - not included in OSDG.")
            print("Please use a research-based threshold or find alternative data.")
            print(f"\nUsing defaults from config:")
            print(f"  For ST mode: {st_default:.2f}")
            print(f"  For Hybrid mode: {hybrid_default:.2f}")
            return  # Exit early
        score_min_raw, score_max_raw, score_stats, bert_scores = get_score_range(texts, target_sdg=target_sdg)

        # Round down to nearest increment for min, round up for max
        step = args.step
        score_min = math.floor(score_min_raw / step) * step
        score_max = math.ceil(score_max_raw / step) * step

        # Generate threshold range based on actual scores (rounded to nearest increment)
        thresholds = np.arange(score_min, score_max + step, step)
        thresholds = [round(t, 2) for t in thresholds]
        print(f"Testing {len(thresholds)} thresholds from {score_min:.2f} to {score_max:.2f}")

        # Check if CV is requested (--cv 1 means single run, no CV)
        threshold_info = {}
        if args.cv is not None and args.cv > 1:
            # Run cross-validation - compute threshold_info after CV using full data stats
            avg_threshold, _, fold_details = optimize_threshold_with_cv(
                texts, labels, thresholds, n_folds=args.cv, target_sdg=target_sdg
            )
            best_threshold = avg_threshold
            best_result = None

            # Compute threshold_info after CV using full data stats
            if score_stats and bert_scores:
                st_std = score_stats.get('st_std')
                bert_std = score_stats.get('bert_std')
                bert_mean = score_stats.get('bert_mean')
                if st_std and st_std > 0 and bert_std and bert_std > 0 and bert_mean is not None:
                    st_mean = score_stats['st_mean']
                    # Use average threshold from CV
                    threshold_z = (avg_threshold - st_mean) / st_std
                    sdgbert_threshold = threshold_z * bert_std + bert_mean

                    # Compute metrics using sdgBERT threshold
                    predictions_bert = [1 if score >= sdgbert_threshold else 0 for score in bert_scores]
                    precision_bert, recall_bert, f1_bert, _ = precision_recall_fscore_support(
                        labels, predictions_bert, average='binary', zero_division=0
                    )
                    accuracy_bert = accuracy_score(labels, predictions_bert)

                    threshold_info = {
                        'st_threshold': avg_threshold,
                        'threshold_z': threshold_z,
                        'sdgbert_threshold': sdgbert_threshold,
                        'sdgbert_f1': f1_bert,
                        'sdgbert_precision': precision_bert,
                        'sdgbert_recall': recall_bert,
                        'sdgbert_accuracy': accuracy_bert,
                        'st_precision': np.mean([d['precision'] for d in fold_details])
                    }

                    # Compute ST and sdgBERT weights based on precision ratio
                    st_precision = np.mean([d['precision'] for d in fold_details])
                    total_precision = st_precision + precision_bert
                    if total_precision > 0:
                        st_weight = st_precision / total_precision
                        sdgbert_weight = precision_bert / total_precision
                    else:
                        st_weight = 0.5
                        sdgbert_weight = 0.5

                    threshold_info['st_weight'] = st_weight
                    threshold_info['sdgbert_weight'] = sdgbert_weight
                    threshold_info['hybrid_threshold'] = (st_weight * avg_threshold) + (sdgbert_weight * sdgbert_threshold)

                    print(f"\n{'='*50}")
                    print("THRESHOLD CONVERSION (CV-based)")
                    print(f"{'='*50}")
                    print(f"ST avg threshold:      {avg_threshold:.3f}")
                    print(f"ST mean:              {st_mean:.3f}")
                    print(f"ST std:               {st_std:.3f}")
                    print(f"Threshold z-score:    {threshold_z:.3f}")
                    print(f"sdgBERT threshold:   {sdgbert_threshold:.3f}")
                    print(f"sdgBERT mean:         {bert_mean:.3f}")
                    print(f"sdgBERT std:          {bert_std:.3f}")
                    print(f"\nsdgBERT Threshold Metrics:")
                    print(f"  F1:       {f1_bert:.3f}")
                    print(f"  Precision:{precision_bert:.3f}")
                    print(f"  Recall:   {recall_bert:.3f}")
                    print(f"  Accuracy: {accuracy_bert:.3f}")
                    print(f"\nPrecision-based Ensemble Weights:")
                    print(f"  ST weight:       {st_weight:.3f}")
                    print(f"  sdgBERT weight:  {sdgbert_weight:.3f}")
                    print(f"  Hybrid threshold: {(st_weight * avg_threshold) + (sdgbert_weight * sdgbert_threshold):.3f}")
        else:
            # Run single optimization (--cv 1 or no --cv flag)
            best_threshold, results, threshold_info = optimize_threshold(
                texts, labels, thresholds, target_sdg=target_sdg, stats=score_stats, bert_scores=bert_scores
            )

            # Print results
            print_results(results)

            # Find best result object
            best_result = next(r for r in results if r.threshold == best_threshold)

            print("\n" + "=" * 70)
            print(f"BEST RESULT FOR SDG {target_sdg}")
            print("=" * 70)
            print(f"Threshold:  {best_threshold:.2f}")
            print(f"F1 Score:   {best_result.f1:.3f}")
            print(f"Precision:  {best_result.precision:.3f}")
            print(f"Recall:     {best_result.recall:.3f}")
            print(f"Accuracy:   {best_result.accuracy:.3f}")

    elif mode == "multiple":
        # Multiple SDGs mode - optimize each SDG separately
        print("\n" + "=" * 70)
        print(f"OPTIMIZING THRESHOLDS FOR SDGs: {target_sdgs}")
        print("=" * 70)

        all_results = {}
        fold_details_all = {}  # Store fold details per SDG
        threshold_info_all = {}  # Store threshold info per SDG

        for sdg in target_sdgs:
            print(f"\n{'='*50}")
            print(f"Processing SDG {sdg}...")
            print(f"{'='*50}")

            # Get samples for this SDG
            pos_df = [t for t, l in zip(osdg_data['all_texts'], osdg_data['all_labels']) if l == sdg]
            neg_df = [t for t, l in zip(osdg_data['all_texts'], osdg_data['all_labels']) if l != sdg]

            # Check for insufficient positive samples
            if len(pos_df) == 0:
                print(f"⚠️  WARNING: No samples found for SDG {sdg}!")
                print(f"   Cannot optimize threshold - skipping.")
                all_results[sdg] = None  # N/A
                continue

            # Compute per-SDG sample count if --pct-samples was used
            sdg_n_samples = n_samples  # default from --n-samples
            if args.pct_samples is not None:
                neg_count = len(neg_df)
                sdg_n_samples = int(args.pct_samples * 2 * min(len(pos_df), neg_count))

            texts, labels = get_balanced_samples(pos_df, neg_df, n_samples=sdg_n_samples)

            # Compute score range (get_score_range returns 4 values: min, max, stats, bert_scores)
            score_min_raw, score_max_raw, score_stats, bert_scores = get_score_range(texts, target_sdg=sdg)

            step = args.step
            score_min = math.floor(score_min_raw / step) * step
            score_max = math.ceil(score_max_raw / step) * step

            thresholds = np.arange(score_min, score_max + step, step)
            thresholds = [round(t, 2) for t in thresholds]

            # Check if CV is requested (--cv 1 means single run, no CV)
            fold_details = None
            threshold_info = None
            if args.cv is not None and args.cv > 1:
                # Run cross-validation
                avg_threshold, _, fold_details = optimize_threshold_with_cv(
                    texts, labels, thresholds, n_folds=args.cv, target_sdg=sdg
                )
                all_results[sdg] = avg_threshold
                fold_details_all[sdg] = fold_details

                # Compute threshold_info after CV using full data stats
                if score_stats and bert_scores:
                    st_std = score_stats.get('st_std')
                    bert_std = score_stats.get('bert_std')
                    bert_mean = score_stats.get('bert_mean')
                    if st_std and st_std > 0 and bert_std and bert_std > 0 and bert_mean is not None:
                        st_mean = score_stats['st_mean']
                        # Use average threshold from CV
                        threshold_z = (avg_threshold - st_mean) / st_std
                        sdgbert_threshold = threshold_z * bert_std + bert_mean

                        # Compute metrics using sdgBERT threshold
                        predictions_bert = [1 if score >= sdgbert_threshold else 0 for score in bert_scores]
                        precision_bert, recall_bert, f1_bert, _ = precision_recall_fscore_support(
                            labels, predictions_bert, average='binary', zero_division=0
                        )
                        accuracy_bert = accuracy_score(labels, predictions_bert)

                        threshold_info = {
                            'st_threshold': avg_threshold,
                            'threshold_z': threshold_z,
                            'sdgbert_threshold': sdgbert_threshold,
                            'sdgbert_f1': f1_bert,
                            'sdgbert_precision': precision_bert,
                            'sdgbert_recall': recall_bert,
                            'sdgbert_accuracy': accuracy_bert,
                            'st_precision': np.mean([d['precision'] for d in fold_details])
                        }

                        # Compute ST and sdgBERT weights based on precision ratio
                        st_precision = np.mean([d['precision'] for d in fold_details])
                        total_precision = st_precision + precision_bert
                        if total_precision > 0:
                            st_weight = st_precision / total_precision
                            sdgbert_weight = precision_bert / total_precision
                        else:
                            st_weight = 0.5
                            sdgbert_weight = 0.5

                        threshold_info['st_weight'] = st_weight
                        threshold_info['sdgbert_weight'] = sdgbert_weight
                        threshold_info['hybrid_threshold'] = (st_weight * avg_threshold) + (sdgbert_weight * sdgbert_threshold)

                        print(f"\nPrecision-based Ensemble Weights:")
                        print(f"  ST weight:       {st_weight:.3f}")
                        print(f"  sdgBERT weight:  {sdgbert_weight:.3f}")
                        print(f"  Hybrid threshold: {(st_weight * avg_threshold) + (sdgbert_weight * sdgbert_threshold):.3f}")

                # Print CV results
                print(f"\nCV Results for SDG {sdg}:")
                print(f"  Average threshold: {avg_threshold:.2f}")
                print(f"  Per-fold thresholds: {[f'{t:.2f}' for t in [d['best_threshold'] for d in fold_details]]}")
                print(f"  Mean F1: {np.mean([d['f1'] for d in fold_details]):.3f}")

                # Store threshold_info for CV mode
                threshold_info_all[sdg] = threshold_info
            else:
                # Single optimization
                best_thresh, _, threshold_info = optimize_threshold(
                    texts, labels, thresholds, target_sdg=sdg, stats=score_stats, bert_scores=bert_scores
                )
                all_results[sdg] = best_thresh
                threshold_info_all[sdg] = threshold_info

        # Print summary
        print("\n" + "=" * 70)
        print("OPTIMAL THRESHOLDS FOR SPECIFIED SDGs")
        print("=" * 70)
        for sdg in target_sdgs:
            thresh = all_results.get(sdg)
            if thresh is None:
                print(f"SDG {sdg:2d}: N/A (no samples in dataset)")
            else:
                print(f"SDG {sdg:2d}: {thresh:.2f}")

        best_threshold = all_results
        best_result = None

    elif mode == "all":
        # All SDGs mode - optimize each SDG separately
        print("\n" + "=" * 70)
        print("OPTIMIZING THRESHOLDS FOR ALL SDGs")
        print("=" * 70)

        all_results = {}
        threshold_info_all = {}

        for sdg in range(1, 18):
            print(f"\n{'='*50}")
            print(f"Processing SDG {sdg}...")
            print(f"{'='*50}")

            # Get samples for this SDG
            pos_df = [t for t, l in zip(osdg_data['all_texts'], osdg_data['all_labels']) if l == sdg]
            neg_df = [t for t, l in zip(osdg_data['all_texts'], osdg_data['all_labels']) if l != sdg]

            # Check for insufficient positive samples
            if len(pos_df) == 0:
                print(f"⚠️  WARNING: No samples found for SDG {sdg}!")
                print(f"   Cannot optimize threshold - skipping.")
                all_results[sdg] = None  # N/A
                continue

            # Compute per-SDG sample count if --pct-samples was used
            sdg_n_samples = n_samples  # default from --n-samples
            if args.pct_samples is not None:
                neg_count = len(neg_df)
                sdg_n_samples = int(args.pct_samples * 2 * min(len(pos_df), neg_count))

            texts, labels = get_balanced_samples(pos_df, neg_df, n_samples=sdg_n_samples)

            # Compute score range (get_score_range returns 4 values: min, max, stats, bert_scores)
            score_min_raw, score_max_raw, score_stats, bert_scores = get_score_range(texts, target_sdg=sdg)

            step = args.step
            score_min = math.floor(score_min_raw / step) * step
            score_max = math.ceil(score_max_raw / step) * step

            thresholds = np.arange(score_min, score_max + step, step)
            thresholds = [round(t, 2) for t in thresholds]

            # Check if CV is requested (--cv 1 means single run, no CV)
            threshold_info = None
            if args.cv is not None and args.cv > 1:
                # Run cross-validation
                avg_threshold, _, fold_details = optimize_threshold_with_cv(
                    texts, labels, thresholds, n_folds=args.cv, target_sdg=sdg
                )
                all_results[sdg] = avg_threshold

                # Compute threshold_info after CV using full data stats
                if score_stats and bert_scores:
                    st_std = score_stats.get('st_std')
                    bert_std = score_stats.get('bert_std')
                    bert_mean = score_stats.get('bert_mean')
                    if st_std and st_std > 0 and bert_std and bert_std > 0 and bert_mean is not None:
                        st_mean = score_stats['st_mean']
                        threshold_z = (avg_threshold - st_mean) / st_std
                        sdgbert_threshold = threshold_z * bert_std + bert_mean

                        predictions_bert = [1 if score >= sdgbert_threshold else 0 for score in bert_scores]
                        precision_bert, recall_bert, f1_bert, _ = precision_recall_fscore_support(
                            labels, predictions_bert, average='binary', zero_division=0
                        )
                        accuracy_bert = accuracy_score(labels, predictions_bert)

                        threshold_info = {
                            'st_threshold': avg_threshold,
                            'threshold_z': threshold_z,
                            'sdgbert_threshold': sdgbert_threshold,
                            'sdgbert_f1': f1_bert,
                            'sdgbert_precision': precision_bert,
                            'sdgbert_recall': recall_bert,
                            'sdgbert_accuracy': accuracy_bert,
                            'st_precision': np.mean([d['precision'] for d in fold_details])
                        }

                        st_precision = np.mean([d['precision'] for d in fold_details])
                        total_precision = st_precision + precision_bert
                        if total_precision > 0:
                            st_weight = st_precision / total_precision
                            sdgbert_weight = precision_bert / total_precision
                        else:
                            st_weight = 0.5
                            sdgbert_weight = 0.5

                        threshold_info['st_weight'] = st_weight
                        threshold_info['sdgbert_weight'] = sdgbert_weight

                # Print CV results
                print(f"\nCV Results for SDG {sdg}:")
                print(f"  Average threshold: {avg_threshold:.2f}")
                print(f"  Per-fold thresholds: {[f'{t:.2f}' for t in [d['best_threshold'] for d in fold_details]]}")
                print(f"  Mean F1: {np.mean([d['f1'] for d in fold_details]):.3f}")
            else:
                # Single optimization
                best_thresh, _, threshold_info = optimize_threshold(
                    texts, labels, thresholds, target_sdg=sdg, stats=score_stats, bert_scores=bert_scores
                )
                all_results[sdg] = best_thresh

            # Store threshold_info
            threshold_info_all[sdg] = threshold_info

        # Print summary
        print("\n" + "=" * 70)
        print("OPTIMAL THRESHOLDS FOR ALL SDGs")
        print("=" * 70)
        for sdg, thresh in sorted(all_results.items()):
            if thresh is None:
                print(f"SDG {sdg:2d}: N/A (no samples in dataset)")
            else:
                print(f"SDG {sdg:2d}: {thresh:.2f}")

        best_threshold = all_results
        best_result = None

    elif mode == "combined":
        # Combined mode - use multi-label evaluation
        texts, labels = get_combined_samples(
            osdg_data['all_texts'],
            osdg_data['all_labels'],
            n_samples=n_samples
        )

        # Compute global score range
        print("\nComputing global score distribution...")
        engine = AlignmentEngine(similarity_threshold=0.0)

        all_scores = {sdg: [] for sdg in range(1, 18)}
        for text in tqdm(texts, desc="Computing scores"):
            try:
                result = engine.align_activity(text, use_cache=False)
                for sdg in range(1, 18):
                    all_scores[sdg].append(result['sdg_scores'][sdg]['score'])
            except:
                pass

        # Get global min/max
        all_flat_scores = [s for scores in all_scores.values() for s in scores]
        score_min_raw = min(all_flat_scores)
        score_max_raw = max(all_flat_scores)

        print(f"Score range: {score_min_raw:.3f} to {score_max_raw:.3f}")
        print(f"  Mean: {np.mean(all_flat_scores):.3f}, Median: {np.median(all_flat_scores):.3f}")

        step = args.step
        score_min = math.floor(score_min_raw / step) * step
        score_max = math.ceil(score_max_raw / step) * step

        thresholds = np.arange(score_min, score_max + step, step)
        thresholds = [round(t, 2) for t in thresholds]
        print(f"Testing {len(thresholds)} thresholds from {score_min:.2f} to {score_max:.2f}")

        # Evaluate each threshold using multi-label metrics
        print("\nEvaluating thresholds (combined mode)...")
        results = []
        for thresh in tqdm(thresholds, desc="Testing thresholds"):
            result = evaluate_threshold_combined(thresh, texts, labels, engine)
            results.append(result)

        best = max(results, key=lambda x: x.f1)
        best_threshold = best.threshold
        best_result = best

        print("\n" + "=" * 70)
        print("BEST RESULT (COMBINED MODE)")
        print("=" * 70)
        print(f"Threshold:  {best_threshold:.2f}")
        print(f"Macro F1:   {best_result.f1:.3f}")
        print(f"Precision:  {best_result.precision:.3f}")
        print(f"Recall:     {best_result.recall:.3f}")

    # Save to JSON if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle threshold rounding for different modes
        if mode == "single":
            threshold_to_save = round(best_threshold, 2)
        elif mode in ["multiple", "all"]:
            threshold_to_save = {sdg: round(thresh, 2) if thresh else None for sdg, thresh in best_threshold.items()}
        else:
            threshold_to_save = best_threshold

        json_results = {
            "mode": mode,
            "target_sdg": target_sdg if mode == "single" else (target_sdgs if mode == "multiple" else args.sdg),
            "best_threshold": threshold_to_save,
            "n_samples": args.n_samples,
            "cv_folds": args.cv,
            "step": args.step,
            "n_samples_actual": n_samples
        }

        if mode == "single":
            json_results["n_samples_total"] = len(texts)
            json_results["n_positive"] = sum(labels)
            json_results["n_negative"] = len(labels) - sum(labels)

            if args.cv is not None and args.cv > 1:
                json_results["cv_folds"] = args.cv
                json_results["fold_details"] = fold_details
                json_results["threshold_std"] = float(np.std([d['best_threshold'] for d in fold_details]))
                json_results["mean_f1"] = float(np.mean([d['f1'] for d in fold_details]))
            else:
                json_results["best_result"] = {
                    "f1": best_result.f1,
                    "precision": best_result.precision,
                    "recall": best_result.recall,
                    "accuracy": best_result.accuracy
                }

            # Add threshold conversion info
            if threshold_info and len(threshold_info) > 0:
                json_results["threshold_info"] = {
                    "st_threshold": round(threshold_info.get('st_threshold', 0), 3),
                    "threshold_z": round(threshold_info.get('threshold_z', 0), 3),
                    "sdgbert_threshold": round(threshold_info.get('sdgbert_threshold', 0), 3),
                    "sdgbert_f1": round(threshold_info.get('sdgbert_f1', 0), 3),
                    "sdgbert_precision": round(threshold_info.get('sdgbert_precision', 0), 3),
                    "sdgbert_recall": round(threshold_info.get('sdgbert_recall', 0), 3),
                    "sdgbert_accuracy": round(threshold_info.get('sdgbert_accuracy', 0), 3),
                    "st_precision": round(threshold_info.get('st_precision', 0), 3),
                    "st_weight": round(threshold_info.get('st_weight', 0), 3),
                    "sdgbert_weight": round(threshold_info.get('sdgbert_weight', 0), 3),
                    "hybrid_threshold": round(threshold_info.get('hybrid_threshold', 0), 3)
                }
        elif mode == "multiple":
            # Multiple mode - store per-SDG thresholds and threshold_info
            json_results["threshold_info"] = {}
            for sdg, info in threshold_info_all.items():
                if info:
                    json_results["threshold_info"][str(sdg)] = {
                        "st_threshold": round(info.get('st_threshold', 0), 3),
                        "threshold_z": round(info.get('threshold_z', 0), 3),
                        "sdgbert_threshold": round(info.get('sdgbert_threshold', 0), 3),
                        "sdgbert_f1": round(info.get('sdgbert_f1', 0), 3),
                        "sdgbert_precision": round(info.get('sdgbert_precision', 0), 3),
                        "sdgbert_recall": round(info.get('sdgbert_recall', 0), 3),
                        "sdgbert_accuracy": round(info.get('sdgbert_accuracy', 0), 3),
                        "st_precision": round(info.get('st_precision', 0), 3),
                        "st_weight": round(info.get('st_weight', 0), 3),
                        "sdgbert_weight": round(info.get('sdgbert_weight', 0), 3),
                        "hybrid_threshold": round(info.get('hybrid_threshold', 0), 3)
                    }
        elif mode == "all":
            # All mode - store per-SDG thresholds and threshold_info
            json_results["threshold_info"] = {}
            for sdg, info in threshold_info_all.items():
                if info:
                    json_results["threshold_info"][str(sdg)] = {
                        "st_threshold": round(info.get('st_threshold', 0), 3),
                        "threshold_z": round(info.get('threshold_z', 0), 3),
                        "sdgbert_threshold": round(info.get('sdgbert_threshold', 0), 3),
                        "sdgbert_f1": round(info.get('sdgbert_f1', 0), 3),
                        "sdgbert_precision": round(info.get('sdgbert_precision', 0), 3),
                        "sdgbert_recall": round(info.get('sdgbert_recall', 0), 3),
                        "sdgbert_accuracy": round(info.get('sdgbert_accuracy', 0), 3),
                        "st_precision": round(info.get('st_precision', 0), 3),
                        "st_weight": round(info.get('st_weight', 0), 3),
                        "sdgbert_weight": round(info.get('sdgbert_weight', 0), 3),
                        "hybrid_threshold": round(info.get('hybrid_threshold', 0), 3)
                    }

        with open(output_path, 'w') as f:
            json.dump(json_results, f, indent=2)

        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
