#!/usr/bin/env python3
"""Optimize per-SDG alignment thresholds for ST, sdgBERT, and Hybrid modes.

Uses the weight-optimization split (no overlap with fine-tuning) from both
OSDG and AidData datasets. Evaluates per-SDG independent thresholding:
  prediction = score >= threshold  (NOT top-1 argmax)

Two-pass sweep:
  Pass 1: Coarse grid at 0.01 increments
  Pass 2: Fine grid at 0.001 increments around best region

Constraints:
  - FP rate ceiling: 0.35 per SDG
  - OSDG accuracy: >= 87.6% baseline (for sdgBERT/Hybrid top-1 check)
  - Generalization gap: OOS F1 < 0.90 * val F1 → flagged

Output: Python dict snippet ready to paste into threshold_config.py

Usage:
    python scripts/optimize_thresholds.py
    python scripts/optimize_thresholds.py --sdg-bert-model models/sdg-bert-multilabel/sdg-bert-multilabel-<ts>
    python scripts/optimize_thresholds.py --device cpu
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score, precision_score, recall_score

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT
from src.config.threshold_config import get_threshold

SDG_COLS = [f"SDG{i}" for i in range(1, 18)]
NUM_SDGS = 17
SPLITS_DIR = Path("data/splits")

# Thresholds
COARSE_STEP = 0.01
FINE_STEP = 0.001
FP_CEILING = 0.35
OSDG_ACC_BASELINE = 0.876
GENERALIZATION_GAP = 0.90
MIN_SUPPORT = 50  # SDGs below this in validation get tiered approach

# Score normalization for hybrid mode (matches hybrid_alignment_engine.py)
ST_NORM_DIVISOR = 0.6


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_aiddata_split(csv_path: Path) -> Tuple[List[str], np.ndarray]:
    """Load AidData split → (texts, binary_labels)."""
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["Description"])
    df = df[df["Description"].str.strip() != ""]
    texts = df["Description"].tolist()
    labels = df[SDG_COLS].fillna(0).astype(int).values
    return texts, labels


def load_osdg_split(csv_path: Path, agreement: float = 0.7) -> Tuple[List[str], List[int]]:
    """Load OSDG split → (texts, sdg_labels). Single-label dataset."""
    df = pd.read_csv(csv_path)
    df = df[df["agreement"] >= agreement]
    df = df[df["text"].notna() & (df["text"].str.strip() != "")]
    texts = df["text"].tolist()
    labels = df["sdg"].astype(int).tolist()
    return texts, labels


def load_splits():
    """Load weightopt + outofsample splits for both datasets."""
    # AidData weightopt (multi-label)
    aid_wo_texts, aid_wo_labels = load_aiddata_split(SPLITS_DIR / "aiddata_weightopt.csv")
    aid_oot_texts, aid_oot_labels = load_aiddata_split(SPLITS_DIR / "aiddata_outofsample.csv")

    # OSDG weightopt (single-label)
    osdg_wo_texts, osdg_wo_labels = load_osdg_split(SPLITS_DIR / "osdg_weightopt.csv")
    osdg_oot_texts, osdg_oot_labels = load_osdg_split(SPLITS_DIR / "osdg_outofsample.csv")

    print("Data splits loaded:")
    print(f"  AidData weightopt: {len(aid_wo_texts)}, outofsample: {len(aid_oot_texts)}")
    print(f"  OSDG weightopt: {len(osdg_wo_texts)}, outofsample: {len(osdg_oot_texts)}")

    # Per-SDG positive support in AidData weightopt
    pos_counts = aid_wo_labels.sum(axis=0).astype(int)
    print(f"  AidData positive counts: {pos_counts.tolist()}")

    return {
        "aid_wo": {"texts": aid_wo_texts, "labels": aid_wo_labels},
        "aid_oot": {"texts": aid_oot_texts, "labels": aid_oot_labels},
        "osdg_wo": {"texts": osdg_wo_texts, "labels": osdg_wo_labels},
        "osdg_oot": {"texts": osdg_oot_texts, "labels": osdg_oot_labels},
    }


# ---------------------------------------------------------------------------
# Score pre-computation
# ---------------------------------------------------------------------------

def precompute_st_scores(engine: AlignmentEngine, texts: List[str]) -> np.ndarray:
    """Pre-compute ST cosine similarity scores for all texts.

    Returns: (N, 17) float array — raw cosine similarity for each text × SDG.
    """
    print(f"Pre-computing ST scores for {len(texts)} texts...")
    scores = np.zeros((len(texts), NUM_SDGS), dtype=np.float32)

    for i, text in enumerate(texts):
        result = engine.align_activity(text, return_top_n=None)
        for sdg_num in range(1, 18):
            scores[i, sdg_num - 1] = result['sdg_scores'][sdg_num]['score']

        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(texts)} done")

    print(f"  ST scores: min={scores.min():.4f}, max={scores.max():.4f}, mean={scores.mean():.4f}")
    return scores


def precompute_sdg_bert_scores(classifier: SDGBERTClassifier, texts: List[str],
                                batch_size: int = 16) -> np.ndarray:
    """Pre-compute sdgBERT scores for all texts.

    Returns: (N, 17) float array — sigmoid probabilities for each text × SDG.
    """
    print(f"Pre-computing sdgBERT scores for {len(texts)} texts...")
    all_probs = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        results = classifier.predict_batch(batch, batch_size=len(batch))
        for r in results:
            probs = np.zeros(NUM_SDGS, dtype=np.float32)
            for sdg_num in range(1, 18):
                probs[sdg_num - 1] = r['all_scores'].get(sdg_num, 0.0)
            all_probs.append(probs)

        if (i + batch_size) % 500 < batch_size:
            print(f"  {min(i + batch_size, len(texts))}/{len(texts)} done")

    scores = np.array(all_probs, dtype=np.float32)
    print(f"  sdgBERT scores: min={scores.min():.4f}, max={scores.max():.4f}, mean={scores.mean():.4f}")
    return scores


def compute_hybrid_scores(st_scores: np.ndarray, bert_scores: np.ndarray) -> np.ndarray:
    """Compute hybrid ensemble scores from pre-computed ST and sdgBERT scores.

    Matches the logic in hybrid_alignment_engine.py._combine_scores():
      ensemble = bert_weight * bert_score + st_weight * min(st_raw / 0.6, 1.0)
    """
    hybrid = np.zeros_like(st_scores)
    for sdg_idx in range(NUM_SDGS):
        sdg_num = sdg_idx + 1
        bert_w, st_w = SDG_ENSEMBLE_WEIGHTS.get(sdg_num, (DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT))
        st_normalized = np.minimum(st_scores[:, sdg_idx] / ST_NORM_DIVISOR, 1.0)
        hybrid[:, sdg_idx] = bert_w * bert_scores[:, sdg_idx] + st_w * st_normalized
    return hybrid


def osdg_labels_to_multi(labels: List[int]) -> np.ndarray:
    """Convert OSDG single-label list to (N, 17) one-hot matrix."""
    multi = np.zeros((len(labels), NUM_SDGS), dtype=np.int32)
    for i, sdg in enumerate(labels):
        if 1 <= sdg <= 17:
            multi[i, sdg - 1] = 1
    return multi


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------

def evaluate_threshold(
    scores: np.ndarray,
    labels: np.ndarray,
    sdg_idx: int,
    threshold: float,
) -> Dict:
    """Evaluate a single threshold for one SDG using per-SDG independent rule.

    Args:
        scores: (N, 17) prediction scores
        labels: (N, 17) binary ground truth
        sdg_idx: 0-indexed SDG index (0 = SDG 1, 16 = SDG 17)
        threshold: threshold to evaluate

    Returns:
        Dict with precision, recall, f1, fp_rate, support
    """
    y_true = labels[:, sdg_idx]
    y_score = scores[:, sdg_idx]
    y_pred = (y_score >= threshold).astype(int)

    # Min-1-positive: if a row has no positive predictions across any SDG,
    # force the top-1 SDG as positive. This is done at the per-row level.
    # For per-SDG evaluation, we just evaluate this SDG independently.
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    support = int(y_true.sum())

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fp_rate": fp_rate,
        "support": support,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def evaluate_all_thresholds(
    scores: np.ndarray,
    labels: np.ndarray,
    sdg_idx: int,
    step: float = COARSE_STEP,
    fp_ceiling: float = FP_CEILING,
) -> List[Dict]:
    """Evaluate all thresholds for one SDG at a given step size.

    Returns list of dicts sorted by F1 descending, each with 'threshold' key.
    """
    results = []
    for t_int in range(1, 100):
        threshold = t_int * step
        if threshold > 1.0:
            break
        r = evaluate_threshold(scores, labels, sdg_idx, threshold)
        r["threshold"] = round(threshold, 6)
        if r["fp_rate"] <= fp_ceiling:
            results.append(r)

    results.sort(key=lambda x: x["f1"], reverse=True)
    return results


def optimize_sdg_threshold(
    scores: np.ndarray,
    labels: np.ndarray,
    sdg_idx: int,
    support: int,
) -> Dict:
    """Two-pass threshold optimization for a single SDG.

    Pass 1: Coarse sweep at 0.01 increments
    Pass 2: Fine sweep at 0.001 increments around best region

    For low-support SDGs (< MIN_SUPPORT), use wider search and accept lower F1.
    """
    # Pass 1: Coarse
    coarse = evaluate_all_thresholds(scores, labels, sdg_idx, COARSE_STEP)

    if not coarse:
        # No threshold meets FP ceiling — use highest threshold with minimum FP
        for t_int in range(99, 0, -1):
            t = t_int * COARSE_STEP
            r = evaluate_threshold(scores, labels, sdg_idx, t)
            if r["fp_rate"] <= FP_CEILING:
                r["threshold"] = round(t, 6)
                return {"coarse": r, "fine": r, "final": r, "low_support": support < MIN_SUPPORT}

        # Extreme: return 1.0
        fallback = evaluate_threshold(scores, labels, sdg_idx, 1.0)
        fallback["threshold"] = 1.0
        return {"coarse": fallback, "fine": fallback, "final": fallback, "low_support": True}

    best_coarse = coarse[0]

    # Pass 2: Fine sweep around best coarse threshold
    center = best_coarse["threshold"]
    fine_min = max(0.001, center - 0.05)
    fine_max = min(1.0, center + 0.05)
    fine_results = []
    t = fine_min
    while t <= fine_max:
        r = evaluate_threshold(scores, labels, sdg_idx, round(t, 6))
        r["threshold"] = round(t, 6)
        if r["fp_rate"] <= FP_CEILING:
            fine_results.append(r)
        t += FINE_STEP

    fine_results.sort(key=lambda x: x["f1"], reverse=True)

    if not fine_results:
        best_fine = best_coarse
    else:
        best_fine = fine_results[0]

    # Tie-break: if multiple thresholds have same F1 (within 0.005), pick higher threshold
    # (higher threshold = fewer FPs, more conservative)
    for r in fine_results[1:]:
        if best_fine["f1"] - r["f1"] < 0.005 and r["threshold"] > best_fine["threshold"]:
            best_fine = r

    return {
        "coarse": best_coarse,
        "fine": best_fine,
        "final": best_fine,
        "low_support": support < MIN_SUPPORT,
    }


def evaluate_osdg_top1_accuracy(
    scores: np.ndarray,
    osdg_labels: List[int],
) -> float:
    """Evaluate OSDG top-1 accuracy (argmax matches single label)."""
    preds = np.argmax(scores, axis=1) + 1  # 1-indexed
    correct = sum(1 for p, l in zip(preds, osdg_labels) if p == l)
    return correct / len(osdg_labels) if osdg_labels else 0.0


def compute_macro_f1(
    scores: np.ndarray,
    labels: np.ndarray,
    thresholds: Dict[int, float],
    min_1_positive: bool = True,
) -> Dict:
    """Compute Macro F1 and per-SDG metrics with given thresholds.

    Args:
        scores: (N, 17) prediction scores
        labels: (N, 17) binary ground truth
        thresholds: {sdg_num: threshold}
        min_1_positive: If True, force at least one positive prediction per row

    Returns:
        Dict with macro_f1, per_sdg metrics, overall_fp_rate
    """
    y_pred = np.zeros_like(labels, dtype=np.int32)
    for sdg_num in range(1, 18):
        y_pred[:, sdg_num - 1] = (scores[:, sdg_num - 1] >= thresholds[sdg_num]).astype(int)

    # Min-1-positive fallback
    if min_1_positive:
        for i in range(len(y_pred)):
            if y_pred[i].sum() == 0:
                y_pred[i, scores[i].argmax()] = 1

    per_sdg = {}
    fp_rates = []
    for sdg_num in range(1, 18):
        idx = sdg_num - 1
        tp = int(((y_pred[:, idx] == 1) & (labels[:, idx] == 1)).sum())
        fp = int(((y_pred[:, idx] == 1) & (labels[:, idx] == 0)).sum())
        fn = int(((y_pred[:, idx] == 0) & (labels[:, idx] == 1)).sum())
        tn = int(((y_pred[:, idx] == 0) & (labels[:, idx] == 0)).sum())
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        per_sdg[sdg_num] = {"precision": prec, "recall": rec, "f1": f1, "fp_rate": fpr,
                            "tp": tp, "fp": fp, "fn": fn, "support": int(labels[:, idx].sum())}
        fp_rates.append(fpr)

    macro_f1 = np.mean([v["f1"] for v in per_sdg.values()])
    macro_prec = np.mean([v["precision"] for v in per_sdg.values()])
    macro_rec = np.mean([v["recall"] for v in per_sdg.values()])
    avg_fp_rate = np.mean(fp_rates)

    return {
        "macro_f1": macro_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "avg_fp_rate": avg_fp_rate,
        "per_sdg": per_sdg,
    }


# ---------------------------------------------------------------------------
# Main optimization
# ---------------------------------------------------------------------------

def optimize_mode(
    mode: str,
    scores: np.ndarray,
    labels: np.ndarray,
    osdg_labels: Optional[List[int]] = None,
    osdg_scores: Optional[np.ndarray] = None,
) -> Dict:
    """Optimize thresholds for one mode (st / sdgbert / hybrid).

    Returns dict with per-SDG optimal thresholds and metrics.
    """
    print(f"\n{'='*60}")
    print(f"Optimizing thresholds for mode: {mode}")
    print(f"{'='*60}")

    # Compute per-SDG positive support
    support = labels.sum(axis=0).astype(int)
    print(f"Per-SDG support: {support.tolist()}")

    results = {}
    for sdg_idx in range(NUM_SDGS):
        sdg_num = sdg_idx + 1
        opt = optimize_sdg_threshold(scores, labels, sdg_idx, int(support[sdg_idx]))
        results[sdg_num] = opt

        low_flag = " [LOW SUPPORT]" if opt["low_support"] else ""
        print(f"  SDG {sdg_num:2d}: threshold={opt['final']['threshold']:.3f} "
              f"F1={opt['final']['f1']:.3f} P={opt['final']['precision']:.3f} "
              f"R={opt['final']['recall']:.3f} FP={opt['final']['fp_rate']:.3f} "
              f"(n={support[sdg_idx]}){low_flag}")

    # Extract thresholds
    thresholds = {sdg_num: results[sdg_num]["final"]["threshold"] for sdg_num in range(1, 18)}

    # Compute overall metrics
    metrics = compute_macro_f1(scores, labels, thresholds)
    print(f"\n  Macro F1: {metrics['macro_f1']:.4f}")
    print(f"  Macro Precision: {metrics['macro_precision']:.4f}")
    print(f"  Macro Recall: {metrics['macro_recall']:.4f}")
    print(f"  Avg FP Rate: {metrics['avg_fp_rate']:.4f}")

    # OSDG top-1 accuracy check (if data provided)
    if osdg_labels is not None and osdg_scores is not None:
        osdg_acc = evaluate_osdg_top1_accuracy(osdg_scores, osdg_labels)
        print(f"  OSDG top-1 accuracy: {osdg_acc:.4f}", end="")
        if osdg_acc < OSDG_ACC_BASELINE:
            print(f" *** BELOW BASELINE {OSDG_ACC_BASELINE} ***")
        else:
            print(" OK")

    return {
        "mode": mode,
        "thresholds": thresholds,
        "metrics": metrics,
        "per_sdg": results,
    }


def validate_on_outofsample(
    mode: str,
    oot_scores: np.ndarray,
    oot_labels: np.ndarray,
    thresholds: Dict[int, float],
    osdg_oot_labels: Optional[List[int]] = None,
    osdg_oot_scores: Optional[np.ndarray] = None,
    val_metrics: Dict = None,
) -> Dict:
    """Validate thresholds on out-of-sample set. Check generalization gap."""
    metrics = compute_macro_f1(oot_scores, oot_labels, thresholds)

    result = {
        "mode": mode,
        "macro_f1": metrics["macro_f1"],
        "macro_precision": metrics["macro_precision"],
        "macro_recall": metrics["macro_recall"],
        "avg_fp_rate": metrics["avg_fp_rate"],
        "per_sdg": metrics["per_sdg"],
    }

    # Generalization gap check
    if val_metrics is not None:
        gap = val_metrics["macro_f1"] * GENERALIZATION_GAP
        if metrics["macro_f1"] < gap:
            result["generalization_flag"] = (
                f"OOS F1 ({metrics['macro_f1']:.4f}) < {GENERALIZATION_GAP} * "
                f"val F1 ({val_metrics['macro_f1']:.4f} = {gap:.4f})"
            )
            print(f"  *** GENERALIZATION GAP: {result['generalization_flag']}")

    # OSDG accuracy
    if osdg_oot_labels is not None and osdg_oot_scores is not None:
        osdg_acc = evaluate_osdg_top1_accuracy(osdg_oot_scores, osdg_oot_labels)
        result["osdg_accuracy"] = osdg_acc

    return result


def format_threshold_config(thresholds: Dict[int, float], mode_name: str) -> str:
    """Format thresholds as Python dict snippet for threshold_config.py."""
    sdg_names = {
        1: "No Poverty", 2: "Zero Hunger", 3: "Good Health", 4: "Quality Education",
        5: "Gender Equality", 6: "Clean Water", 7: "Affordable Energy",
        8: "Decent Work", 9: "Innovation", 10: "Reduced Inequalities",
        11: "Sustainable Cities", 12: "Responsible Consumption", 13: "Climate Action",
        14: "Life Below Water", 15: "Life on Land", 16: "Peace and Justice",
        17: "Partnerships",
    }
    lines = [f'"{mode_name}": {{']
    lines.append(f'    "default": {round(np.mean(list(thresholds.values())), 2)},')
    lines.append(f'    "description": "Optimized thresholds for {mode_name} mode",')
    lines.append('')
    lines.append('    "sdg_specific": {')
    for sdg_num in range(1, 18):
        t = thresholds[sdg_num]
        name = sdg_names[sdg_num]
        comma = "," if sdg_num < 17 else ","
        lines.append(f'        {sdg_num}: {t:.3f}{comma}  # {name}')
    lines.append('    }')
    lines.append('}')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Optimize SDG alignment thresholds")
    parser.add_argument("--sdg-bert-model", default=None,
                        help="Path to fine-tuned sdgBERT model (default: sadickam/sdgBERT)")
    parser.add_argument("--device", default=None, help="Force device (cpu/mps/cuda)")
    parser.add_argument("--fp-ceiling", type=float, default=FP_CEILING,
                        help=f"Max FP rate per SDG (default: {FP_CEILING})")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-st", action="store_true", help="Skip ST mode")
    parser.add_argument("--skip-bert", action="store_true", help="Skip sdgBERT mode")
    parser.add_argument("--skip-hybrid", action="store_true", help="Skip Hybrid mode")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Load data
    splits = load_splits()

    # Initialize engines
    print("\nInitializing Sentence Transformer engine...")
    st_engine = AlignmentEngine()

    sdg_bert = None
    if not args.skip_bert or not args.skip_hybrid:
        model_name = args.sdg_bert_model or "sadickam/sdgBERT"
        print(f"\nInitializing sdgBERT: {model_name}")
        sdg_bert = SDGBERTClassifier(model_name=model_name, device=args.device)

    # --- Pre-compute scores ---
    # Weight-opt set (for threshold optimization)
    aid_wo = splits["aid_wo"]
    osdg_wo = splits["osdg_wo"]

    # Out-of-sample set (for validation)
    aid_oot = splits["aid_oot"]
    osdg_oot = splits["osdg_oot"]

    # AidData multi-label labels
    aid_wo_labels = aid_wo["labels"]
    aid_oot_labels = aid_oot["labels"]
    # OSDG single-label → multi-label conversion for evaluation
    osdg_wo_multi = osdg_labels_to_multi(osdg_wo["labels"])
    osdg_oot_multi = osdg_labels_to_multi(osdg_oot["labels"])

    # Combined AidData + OSDG for weightopt evaluation
    # (OSDG contributes to per-SDG metrics, especially for low-support SDGs)
    combined_wo_labels = np.vstack([aid_wo_labels, osdg_wo_multi])
    combined_wo_texts = aid_wo["texts"] + osdg_wo["texts"]
    combined_oot_labels = np.vstack([aid_oot_labels, osdg_oot_multi])
    combined_oot_texts = aid_oot["texts"] + osdg_oot["texts"]

    # ST scores
    print("\n--- Pre-computing ST scores ---")
    st_wo_scores = precompute_st_scores(st_engine, combined_wo_texts)
    st_oot_scores = precompute_st_scores(st_engine, combined_oot_texts)

    # sdgBERT scores
    bert_wo_scores = None
    bert_oot_scores = None
    if sdg_bert is not None:
        print("\n--- Pre-computing sdgBERT scores ---")
        bert_wo_scores = precompute_sdg_bert_scores(sdg_bert, combined_wo_texts)
        bert_oot_scores = precompute_sdg_bert_scores(sdg_bert, combined_oot_texts)

    # Hybrid scores
    hybrid_wo_scores = None
    hybrid_oot_scores = None
    if st_wo_scores is not None and bert_wo_scores is not None:
        print("\n--- Computing Hybrid scores ---")
        hybrid_wo_scores = compute_hybrid_scores(st_wo_scores, bert_wo_scores)
        hybrid_oot_scores = compute_hybrid_scores(st_oot_scores, bert_oot_scores)

    # --- Optimize thresholds for each mode ---
    all_results = {}

    # ST mode
    if not args.skip_st:
        # For OSDG top-1 accuracy, use only AidData subset (OSDG uses original texts)
        osdg_wo_st_scores = st_wo_scores[len(aid_wo["texts"]):]
        osdg_oot_st_scores = st_oot_scores[len(aid_oot["texts"]):]

        st_result = optimize_mode(
            "st", st_wo_scores, combined_wo_labels,
            osdg_labels=osdg_wo["labels"],
            osdg_scores=osdg_wo_st_scores,
        )
        all_results["st"] = st_result

        # Out-of-sample validation
        st_oot = validate_on_outofsample(
            "st", st_oot_scores, combined_oot_labels, st_result["thresholds"],
            osdg_oot_labels=osdg_oot["labels"],
            osdg_oot_scores=osdg_oot_st_scores,
            val_metrics=st_result["metrics"],
        )
        all_results["st_oot"] = st_oot

    # sdgBERT mode
    if not args.skip_bert and bert_wo_scores is not None:
        osdg_wo_bert_scores = bert_wo_scores[len(aid_wo["texts"]):]
        osdg_oot_bert_scores = bert_oot_scores[len(aid_oot["texts"]):]

        bert_result = optimize_mode(
            "sdgbert", bert_wo_scores, combined_wo_labels,
            osdg_labels=osdg_wo["labels"],
            osdg_scores=osdg_wo_bert_scores,
        )
        all_results["sdgbert"] = bert_result

        bert_oot = validate_on_outofsample(
            "sdgbert", bert_oot_scores, combined_oot_labels, bert_result["thresholds"],
            osdg_oot_labels=osdg_oot["labels"],
            osdg_oot_scores=osdg_oot_bert_scores,
            val_metrics=bert_result["metrics"],
        )
        all_results["sdgbert_oot"] = bert_oot

    # Hybrid mode
    if not args.skip_hybrid and hybrid_wo_scores is not None:
        osdg_wo_hybrid_scores = hybrid_wo_scores[len(aid_wo["texts"]):]
        osdg_oot_hybrid_scores = hybrid_oot_scores[len(aid_oot["texts"]):]

        hybrid_result = optimize_mode(
            "hybrid", hybrid_wo_scores, combined_wo_labels,
            osdg_labels=osdg_wo["labels"],
            osdg_scores=osdg_wo_hybrid_scores,
        )
        all_results["hybrid"] = hybrid_result

        hybrid_oot = validate_on_outofsample(
            "hybrid", hybrid_oot_scores, combined_oot_labels, hybrid_result["thresholds"],
            osdg_oot_labels=osdg_oot["labels"],
            osdg_oot_scores=osdg_oot_hybrid_scores,
            val_metrics=hybrid_result["metrics"],
        )
        all_results["hybrid_oot"] = hybrid_oot

    # --- Summary ---
    print(f"\n{'='*60}")
    print("THRESHOLD OPTIMIZATION SUMMARY")
    print(f"{'='*60}")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"FP ceiling: {args.fp_ceiling}")
    print(f"Seed: {args.seed}")
    print()

    for mode_key in ["st", "sdgbert", "hybrid"]:
        if mode_key not in all_results:
            continue
        result = all_results[mode_key]
        oot = all_results.get(f"{mode_key}_oot", {})

        print(f"\n--- {mode_key.upper()} ---")
        print(f"  Val Macro F1: {result['metrics']['macro_f1']:.4f}")
        if "macro_f1" in oot:
            print(f"  OOS Macro F1: {oot['macro_f1']:.4f}")
        if "osdg_accuracy" in oot:
            print(f"  OOS OSDG accuracy: {oot['osdg_accuracy']:.4f}")
        if "generalization_flag" in oot:
            print(f"  *** {oot['generalization_flag']}")
        print()
        for sdg_num in range(1, 18):
            t = result["thresholds"][sdg_num]
            m = result["per_sdg"][sdg_num]["final"]
            print(f"  SDG {sdg_num:2d}: t={t:.3f}  F1={m['f1']:.3f}  "
                  f"P={m['precision']:.3f}  R={m['recall']:.3f}  FP={m['fp_rate']:.3f}")

    # --- Output config snippets ---
    print(f"\n{'='*60}")
    print("CONFIG SNIPPETS FOR threshold_config.py")
    print(f"{'='*60}")

    mode_map = {"st": "sentence_transformer", "sdgbert": "sdgbert", "hybrid": "hybrid"}
    for mode_key, config_key in mode_map.items():
        if mode_key not in all_results:
            continue
        print(f"\n# {config_key}")
        print(format_threshold_config(all_results[mode_key]["thresholds"], config_key))
        print()

    # Save JSON output
    if args.output:
        output = {
            "timestamp": datetime.now().isoformat(),
            "fp_ceiling": args.fp_ceiling,
            "seed": args.seed,
            "sdg_bert_model": args.sdg_bert_model or "sadickam/sdgBERT",
        }
        for mode_key in ["st", "sdgbert", "hybrid"]:
            if mode_key not in all_results:
                continue
            result = all_results[mode_key]
            oot = all_results.get(f"{mode_key}_oot", {})
            output[mode_key] = {
                "thresholds": result["thresholds"],
                "val_macro_f1": result["metrics"]["macro_f1"],
                "oos_macro_f1": oot.get("macro_f1"),
                "oos_osdg_accuracy": oot.get("osdg_accuracy"),
                "per_sdg": {
                    str(sdg_num): {
                        "threshold": result["per_sdg"][sdg_num]["final"]["threshold"],
                        "f1": result["per_sdg"][sdg_num]["final"]["f1"],
                        "precision": result["per_sdg"][sdg_num]["final"]["precision"],
                        "recall": result["per_sdg"][sdg_num]["final"]["recall"],
                        "fp_rate": result["per_sdg"][sdg_num]["final"]["fp_rate"],
                    }
                    for sdg_num in range(1, 18)
                },
            }

        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()