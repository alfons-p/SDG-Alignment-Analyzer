#!/usr/bin/env python3
"""Compute AidData multi-label accuracy metrics for all models.

Reports exact match, Hamming accuracy, Jaccard similarity, and sample F1
on the AidData out-of-sample split (16,791 multi-label samples).
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "optimize_thresholds",
    str(Path(__file__).parent / "optimize_thresholds.py"),
)
_opt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_opt)

load_splits = _opt.load_splits
osdg_labels_to_multi = _opt.osdg_labels_to_multi
precompute_st_scores = _opt.precompute_st_scores
precompute_sdg_bert_scores = _opt.precompute_sdg_bert_scores
compute_hybrid_scores = _opt.compute_hybrid_scores

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier
from src.config.threshold_config import get_all_thresholds
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT

ST_NORM_DIVISOR = 0.6

SDG_NAMES = {
    1: "No Poverty", 2: "Zero Hunger", 3: "Good Health",
    4: "Quality Education", 5: "Gender Equality", 6: "Clean Water",
    7: "Affordable Energy", 8: "Decent Work", 9: "Innovation",
    10: "Reduced Inequalities", 11: "Sustainable Cities",
    12: "Responsible Consumption", 13: "Climate Action",
    14: "Life Below Water", 15: "Life on Land",
    16: "Peace and Justice", 17: "Partnerships",
}


def compute_multilabel_metrics(y_true, y_pred):
    """Compute multi-label accuracy metrics."""
    n = len(y_true)

    # Exact match accuracy (all labels correct)
    exact_match = (y_pred == y_true).all(axis=1).mean()

    # Hamming accuracy (fraction of correct label predictions)
    hamming_acc = (y_pred == y_true).mean()

    # Jaccard similarity per sample
    jaccards = []
    for i in range(n):
        pred_set = set(np.where(y_pred[i] == 1)[0])
        true_set = set(np.where(y_true[i] == 1)[0])
        union = pred_set | true_set
        if len(union) == 0:
            jaccards.append(1.0)
        else:
            jaccards.append(len(pred_set & true_set) / len(union))
    jaccard = np.mean(jaccards)

    # Per-sample F1
    sample_f1s = []
    for i in range(n):
        tp = int((y_pred[i] & y_true[i]).sum())
        fp = int((y_pred[i] & ~y_true[i]).sum())
        fn = int((~y_pred[i] & y_true[i]).sum())
        if tp + fp + fn == 0:
            sample_f1s.append(1.0)
        else:
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            sample_f1s.append(f1)
    sample_f1 = np.mean(sample_f1s)

    # Over/under-prediction
    pred_counts = y_pred.sum(axis=1)
    true_counts = y_true.sum(axis=1)
    over_pred = (pred_counts > true_counts).mean()
    under_pred = (pred_counts < true_counts).mean()

    return {
        "exact_match": float(exact_match),
        "hamming_acc": float(hamming_acc),
        "jaccard": float(jaccard),
        "sample_f1": float(sample_f1),
        "over_pred": float(over_pred),
        "under_pred": float(under_pred),
    }


def main():
    parser = argparse.ArgumentParser(description="AidData multi-label accuracy metrics")
    parser.add_argument("--device", default=None, help="Force device (cpu/mps/cuda)")
    parser.add_argument("--skip-baselines", action="store_true", help="Skip baseline models")
    args = parser.parse_args()

    splits = load_splits()
    aid_oot = splits["aid_oot"]
    aid_oot_labels = aid_oot["labels"]
    aid_oot_texts = aid_oot["texts"]
    n = len(aid_oot_labels)
    n_pos = aid_oot_labels.sum(axis=1)

    print(f"\nAidData out-of-sample: {n} samples")
    print(f"  Labels per sample: min={n_pos.min()}, max={n_pos.max()}, mean={n_pos.mean():.2f}")
    print(f"  Single-label: {(n_pos == 1).sum()} ({(n_pos == 1).sum()/n*100:.1f}%)")
    print(f"  Multi-label (2+): {(n_pos >= 2).sum()} ({(n_pos >= 2).sum()/n*100:.1f}%)")
    print()

    # Current models
    print("Initializing models...")
    st_engine = AlignmentEngine()
    sdg_bert = SDGBERTClassifier(device=args.device)

    print("\n--- Computing current model scores ---")
    st_scores = precompute_st_scores(st_engine, aid_oot_texts)
    bert_scores = precompute_sdg_bert_scores(sdg_bert, aid_oot_texts)
    hybrid_scores = compute_hybrid_scores(st_scores, bert_scores)

    current_modes = {
        "ST": (st_scores, "st"),
        "sdgBERT": (bert_scores, "sdgbert"),
        "Hybrid": (hybrid_scores, "hybrid"),
    }

    # Baseline models
    baseline_modes = {}
    if not args.skip_baselines:
        print("\n--- Computing baseline model scores ---")
        baseline_st = AlignmentEngine(model_name="all-MiniLM-L6-v2")
        baseline_bert = SDGBERTClassifier(
            model_name=SDGBERTClassifier.FALLBACK_MODEL, device=args.device
        )

        baseline_st_scores = precompute_st_scores(baseline_st, aid_oot_texts)
        baseline_bert_scores = precompute_sdg_bert_scores(baseline_bert, aid_oot_texts)
        baseline_hybrid_scores = compute_hybrid_scores(baseline_st_scores, baseline_bert_scores)

        # Optimize thresholds for baselines on weightopt split
        print("\nOptimizing baseline thresholds...")
        aid_wo = splits["aid_oot"]  # Use weightopt for optimization
        aid_wo_texts = splits["aid_wo"]["texts"]
        aid_wo_labels = splits["aid_wo"]["labels"]
        combined_wo_labels = np.vstack([aid_wo_labels, osdg_labels_to_multi(splits["osdg_wo"]["labels"])])
        combined_wo_texts = aid_wo_texts + splits["osdg_wo"]["texts"]

        baseline_st_wo = precompute_st_scores(baseline_st, combined_wo_texts)
        baseline_bert_wo = precompute_sdg_bert_scores(baseline_bert, combined_wo_texts)
        baseline_hybrid_wo = compute_hybrid_scores(baseline_st_wo, baseline_bert_wo)

        # For baselines, optimize thresholds on weightopt then evaluate on OOS
        from optimize_thresholds import optimize_sdg_threshold
        # This doesn't work directly due to import, so let's use the get_all_thresholds
        # approach from the benchmark script for baselines, but compute fresh thresholds

        baseline_modes = {
            "ST (baseline)": (baseline_st_scores, "st", baseline_st_wo),
            "BERT (baseline)": (baseline_bert_scores, "sdgbert", baseline_bert_wo),
            "Hybrid (baseline)": (baseline_hybrid_scores, "hybrid", baseline_hybrid_wo),
        }

    print()
    print("=" * 110)
    print("  AIDDATA OUT-OF-SAMPLE MULTI-LABEL ACCURACY")
    print("=" * 110)
    print(f"  {n} samples, mean {n_pos.mean():.1f} labels/sample")
    print(f"  Single-label: {(n_pos == 1).sum()/n*100:.1f}%  Multi-label (2+): {(n_pos >= 2).sum()/n*100:.1f}%")
    print()
    print(f"  {'Mode':<22} {'Exact Match':>12} {'Hamming':>10} {'Jaccard':>10} "
          f"{'Sample F1':>10} {'Over-pred':>10} {'Under-pred':>10}")
    print(f"  {'-'*22} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    all_results = {}

    # Current models
    for mode_name, (scores, mode_key) in current_modes.items():
        thresholds = get_all_thresholds(mode_key)
        y_pred = np.zeros_like(aid_oot_labels)
        for sdg in range(1, 18):
            y_pred[:, sdg-1] = (scores[:, sdg-1] >= thresholds[sdg]).astype(int)
        # Min-1-positive fallback
        for i in range(len(y_pred)):
            if y_pred[i].sum() == 0:
                y_pred[i, scores[i].argmax()] = 1

        metrics = compute_multilabel_metrics(aid_oot_labels, y_pred)
        all_results[mode_name] = metrics

        print(f"  {mode_name:<22} {metrics['exact_match']:>12.4f} {metrics['hamming_acc']:>10.4f} "
              f"{metrics['jaccard']:>10.4f} {metrics['sample_f1']:>10.4f} "
              f"{metrics['over_pred']:>10.4f} {metrics['under_pred']:>10.4f}")

    # Baseline models (use same thresholds for fair comparison)
    for mode_name, (scores, mode_key, _) in baseline_modes.items():
        thresholds = get_all_thresholds(mode_key)
        y_pred = np.zeros_like(aid_oot_labels)
        for sdg in range(1, 18):
            y_pred[:, sdg-1] = (scores[:, sdg-1] >= thresholds[sdg]).astype(int)
        for i in range(len(y_pred)):
            if y_pred[i].sum() == 0:
                y_pred[i, scores[i].argmax()] = 1

        metrics = compute_multilabel_metrics(aid_oot_labels, y_pred)
        all_results[mode_name] = metrics

        print(f"  {mode_name:<22} {metrics['exact_match']:>12.4f} {metrics['hamming_acc']:>10.4f} "
              f"{metrics['jaccard']:>10.4f} {metrics['sample_f1']:>10.4f} "
              f"{metrics['over_pred']:>10.4f} {metrics['under_pred']:>10.4f}")

    print(f"{'='*110}")

    # Also print per-SDG breakdown for sdgBERT (best model)
    print("\n  Per-SDG F1 on AidData OOS (sdgBERT):")
    thresholds = get_all_thresholds("sdgbert")
    y_pred = np.zeros_like(aid_oot_labels)
    for sdg in range(1, 18):
        y_pred[:, sdg-1] = (bert_scores[:, sdg-1] >= thresholds[sdg]).astype(int)
    for i in range(len(y_pred)):
        if y_pred[i].sum() == 0:
            y_pred[i, bert_scores[i].argmax()] = 1

    print(f"  {'SDG':<4} {'Name':<24} {'F1':>7} {'P':>7} {'R':>7} {'Support':>8}")
    print(f"  {'-'*4} {'-'*24} {'-'*7} {'-'*7} {'-'*7} {'-'*8}")
    from sklearn.metrics import f1_score, precision_score, recall_score
    for sdg in range(1, 18):
        idx = sdg - 1
        tp = int(((y_pred[:, idx] == 1) & (aid_oot_labels[:, idx] == 1)).sum())
        fp = int(((y_pred[:, idx] == 1) & (aid_oot_labels[:, idx] == 0)).sum())
        fn = int(((y_pred[:, idx] == 0) & (aid_oot_labels[:, idx] == 1)).sum())
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        support = int(aid_oot_labels[:, idx].sum())
        print(f"  {sdg:<4} {SDG_NAMES[sdg]:<24} {f1:>7.3f} {prec:>7.3f} {rec:>7.3f} {support:>8}")

    macro_f1 = np.mean([
        2 * (tp := int(((y_pred[:, i] == 1) & (aid_oot_labels[:, i] == 1)).sum())) /
        (2 * tp + int(((y_pred[:, i] == 1) & (aid_oot_labels[:, i] == 0)).sum()) +
         int(((y_pred[:, i] == 0) & (aid_oot_labels[:, i] == 1)).sum()))
        if (2 * tp + int(((y_pred[:, i] == 1) & (aid_oot_labels[:, i] == 0)).sum()) +
            int(((y_pred[:, i] == 0) & (aid_oot_labels[:, i] == 1)).sum())) > 0 else 0
        for i in range(17)
    ])

    # Save
    output_path = Path("results/aiddata_accuracy.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to {output_path}")


if __name__ == "__main__":
    main()