#!/usr/bin/env python3
"""Benchmark production models on the sdganalyzer domain-labeled data.

Evaluates ST, sdgBERT, and Hybrid modes using production thresholds from
threshold_config.py (optimized on AidData+OSDG weightopt split).

Usage:
    python scripts/benchmark_sdganalyzer.py
    python scripts/benchmark_sdganalyzer.py --device cpu
    python scripts/benchmark_sdganalyzer.py --skip-hybrid  # skip hybrid mode
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "optimize_thresholds",
    str(Path(__file__).parent / "optimize_thresholds.py"),
)
_opt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_opt)

precompute_st_scores = _opt.precompute_st_scores
precompute_sdg_bert_scores = _opt.precompute_sdg_bert_scores
compute_hybrid_scores = _opt.compute_hybrid_scores
compute_macro_f1 = _opt.compute_macro_f1

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT
from src.config.threshold_config import get_all_thresholds

NUM_SDGS = 17
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


def load_sdganalyzer_labels(path: str = "data/processed/sdganalyzer_ft_labels.csv"):
    """Load sdganalyzer labels and pivot to multi-label binary matrix."""
    df = pd.read_csv(path)
    texts = df["text"].unique().tolist()
    text_to_idx = {t: i for i, t in enumerate(texts)}
    n = len(texts)
    labels = np.zeros((n, NUM_SDGS), dtype=np.int32)
    for _, row in df.iterrows():
        idx = text_to_idx[row["text"]]
        labels[idx, int(row["sdg"]) - 1] = 1
    return texts, labels


def compute_multilabel_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
    """Compute Hamming accuracy and sample F1."""
    n = len(y_true)
    hamming_acc = float((y_pred == y_true).mean())

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
            sample_f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0)
    sample_f1 = float(np.mean(sample_f1s))

    return {"hamming_acc": hamming_acc, "sample_f1": sample_f1}


def _predict(scores: np.ndarray, labels: np.ndarray, thresholds: Dict[int, float]) -> np.ndarray:
    """Apply thresholds with min-1-positive fallback."""
    y_pred = np.zeros_like(labels, dtype=np.int32)
    for sdg_num in range(1, 18):
        y_pred[:, sdg_num - 1] = (scores[:, sdg_num - 1] >= thresholds[sdg_num]).astype(int)
    for i in range(len(y_pred)):
        if y_pred[i].sum() == 0:
            y_pred[i, scores[i].argmax()] = 1
    return y_pred


def evaluate_mode(name, scores, labels, thresholds):
    """Evaluate one mode with given thresholds."""
    metrics = compute_macro_f1(scores, labels, thresholds)
    y_pred = _predict(scores, labels, thresholds)
    ml_metrics = compute_multilabel_metrics(labels, y_pred)
    return {
        "macro_f1": float(metrics["macro_f1"]),
        "macro_precision": float(metrics["macro_precision"]),
        "macro_recall": float(metrics["macro_recall"]),
        "avg_fp_rate": float(metrics["avg_fp_rate"]),
        "hamming_acc": ml_metrics["hamming_acc"],
        "sample_f1": ml_metrics["sample_f1"],
        "per_sdg": {
            str(sdg): {
                "f1": float(metrics["per_sdg"][sdg]["f1"]),
                "precision": float(metrics["per_sdg"][sdg]["precision"]),
                "recall": float(metrics["per_sdg"][sdg]["recall"]),
                "fp_rate": float(metrics["per_sdg"][sdg]["fp_rate"]),
                "support": int(metrics["per_sdg"][sdg]["support"]),
                "threshold": float(thresholds[sdg]),
            }
            for sdg in range(1, 18)
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark production models on sdganalyzer labels")
    parser.add_argument("--device", default=None, help="Force device (cpu/mps/cuda)")
    parser.add_argument("--skip-hybrid", action="store_true", help="Skip hybrid mode")
    parser.add_argument("--output", default="results/sdganalyzer_comparison.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    # Load domain labels
    texts, labels = load_sdganalyzer_labels()
    n = len(texts)
    n_pos = labels.sum(axis=1)
    print(f"\nsdganalyzer domain data: {n} texts, {labels.sum()} positive labels")
    print(f"  Labels per text: min={n_pos.min()}, max={n_pos.max()}, mean={n_pos.mean():.2f}")
    print(f"  Per-SDG support: {dict(zip(range(1,18), labels.sum(axis=0)))}")
    print()

    all_results = {}

    # === ST MODE ===
    print("=" * 80)
    print("  ST MODE (production thresholds)")
    print("=" * 80)
    st_engine = AlignmentEngine()
    st_scores = precompute_st_scores(st_engine, texts)
    st_thresholds = get_all_thresholds("st")
    result = evaluate_mode("ST", st_scores, labels, st_thresholds)
    all_results["ST"] = result
    print(f"    Macro F1: {result['macro_f1']:.4f}  "
          f"Hamming: {result['hamming_acc']:.4f}  "
          f"sF1: {result['sample_f1']:.4f}")

    # === sdgBERT MODE ===
    print("\n" + "=" * 80)
    print("  sdgBERT MODE (production thresholds)")
    print("=" * 80)
    bert = SDGBERTClassifier(device=args.device)
    bert_scores = precompute_sdg_bert_scores(bert, texts)
    bert_thresholds = get_all_thresholds("sdgbert")
    result = evaluate_mode("sdgBERT", bert_scores, labels, bert_thresholds)
    all_results["sdgBERT"] = result
    print(f"    Macro F1: {result['macro_f1']:.4f}  "
          f"Hamming: {result['hamming_acc']:.4f}  "
          f"sF1: {result['sample_f1']:.4f}")

    # === HYBRID MODE ===
    if not args.skip_hybrid:
        print("\n" + "=" * 80)
        print("  HYBRID MODE (production thresholds)")
        print("=" * 80)
        hybrid_scores = compute_hybrid_scores(st_scores, bert_scores)
        hybrid_thresholds = get_all_thresholds("hybrid")
        result = evaluate_mode("Hybrid", hybrid_scores, labels, hybrid_thresholds)
        all_results["Hybrid"] = result
        print(f"    Macro F1: {result['macro_f1']:.4f}  "
              f"Hamming: {result['hamming_acc']:.4f}  "
              f"sF1: {result['sample_f1']:.4f}")

    # === PRINT COMPARISON TABLE ===
    sorted_results = sorted(all_results.items(), key=lambda x: x[1]["macro_f1"], reverse=True)

    print("\n" + "=" * 138)
    print("  MODEL COMPARISON — sdganalyzer DOMAIN DATA (production thresholds)")
    print("=" * 138)
    print(f"\n  {'#':<3} {'Mode':<20} {'Macro F1':>10} {'Macro P':>10} {'Macro R':>10} "
          f"{'Avg FP':>8} {'Hamm Acc':>10} {'Sample F1':>10}")
    print(f"  {'-'*3} {'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")

    for rank, (name, result) in enumerate(sorted_results, 1):
        print(f"  {rank:<3} {name:<20} {result['macro_f1']:>10.4f} "
              f"{result['macro_precision']:>10.4f} {result['macro_recall']:>10.4f} "
              f"{result['avg_fp_rate']:>8.4f} {result['hamming_acc']:>10.4f} "
              f"{result['sample_f1']:>10.4f}")

    # Per-SDG comparison table
    print("\n" + "=" * 80)
    print("  PER-SDG F1 COMPARISON — sdganalyzer DOMAIN DATA (production thresholds)")
    print("=" * 80)

    model_names = [name for name, _ in sorted_results]
    header = f"  {'SDG':<4} {'Name':<24} " + " ".join(f"{n:>10}" for n in model_names)
    print(header)
    print(f"  {'-'*4} {'-'*24} " + " ".join(f"{'-'*10}" for _ in model_names))

    for sdg in range(1, 18):
        name = SDG_NAMES[sdg]
        row = f"  {sdg:<4} {name:<24} "
        for mname in model_names:
            f1 = all_results[mname]["per_sdg"].get(str(sdg), {}).get("f1", 0)
            row += f"{f1:>10.3f} "
        print(row)

    print(f"  {'-'*4} {'-'*24} " + " ".join(f"{'-'*10}" for _ in model_names))
    row = f"  {'':4} {'MACRO F1':<24} "
    for mname in model_names:
        row += f"{all_results[mname]['macro_f1']:>10.4f} "
    print(row)

    # Problem SDGs
    print(f"\n  Problem SDGs (F1 < 0.5) per mode:")
    for name in model_names:
        problems = [(sdg, all_results[name]["per_sdg"][str(sdg)]["f1"])
                     for sdg in range(1, 18)
                     if str(sdg) in all_results[name]["per_sdg"]
                     and all_results[name]["per_sdg"][str(sdg)]["f1"] < 0.5]
        if problems:
            pstr = ", ".join(f"SDG{s}({f:.2f})" for s, f in problems)
            print(f"    {name:<20}: {pstr}")
        else:
            print(f"    {name:<20}: None")

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def convert(obj):
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    serializable = json.loads(json.dumps(all_results, default=convert))
    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"\n  Results saved to {output_path}")