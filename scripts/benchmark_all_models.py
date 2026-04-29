#!/usr/bin/env python3
"""Benchmark all fine-tuned ST and BERT models on the same out-of-sample data.

Models tested:
  ST models (Sentence Transformer):
    1. all-MiniLM-L6-v2 (baseline, no SDG fine-tuning)
    2. sdg-finetuned-20260224 (OSDG only)
    3. sdg-enhanced-finetuned-20260226 (current default / HuggingFace)
    4. sdg-hybrid_enhanced-20260329 (OSDG + Chinese LLM)
    5. sdg-variant-finetuned-20260417 (OSDG + AidData, 5 variants)

  BERT models:
    6. sadickam/sdgBERT (baseline, 16-class softmax, no SDG 17)
    7. sdg-bert-multilabel-20260420 (current, 17-class sigmoid)

For each model: optimize per-SDG thresholds on weightopt, evaluate on out-of-sample.

Usage:
    python scripts/benchmark_all_models.py
    python scripts/benchmark_all_models.py --device cpu
    python scripts/benchmark_all_models.py --skip-st  # skip ST models
    python scripts/benchmark_all_models.py --skip-bert  # skip BERT models
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List

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
precompute_st_scores = _opt.precompute_st_scores
precompute_sdg_bert_scores = _opt.precompute_sdg_bert_scores
compute_hybrid_scores = _opt.compute_hybrid_scores
osdg_labels_to_multi = _opt.osdg_labels_to_multi
evaluate_osdg_top1_accuracy = _opt.evaluate_osdg_top1_accuracy
compute_macro_f1 = _opt.compute_macro_f1
optimize_sdg_threshold = _opt.optimize_sdg_threshold

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT
from src.config.threshold_config import get_all_thresholds

NUM_SDGS = 17
ST_NORM_DIVISOR = 0.6
MODELS_DIR = Path("models")

SDG_NAMES = {
    1: "No Poverty", 2: "Zero Hunger", 3: "Good Health",
    4: "Quality Education", 5: "Gender Equality", 6: "Clean Water",
    7: "Affordable Energy", 8: "Decent Work", 9: "Innovation",
    10: "Reduced Inequalities", 11: "Sustainable Cities",
    12: "Responsible Consumption", 13: "Climate Action",
    14: "Life Below Water", 15: "Life on Land",
    16: "Peace and Justice", 17: "Partnerships",
}

ST_MODELS = {
    "ST baseline (all-MiniLM-L6-v2)": "all-MiniLM-L6-v2",
    "ST OSDG-only (finetuned-20260224)": str(MODELS_DIR / "sdg-finetuned/sdg-finetuned-20260224_184210"),
    "ST current (enhanced-20260226)": str(MODELS_DIR / "sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509"),
    "ST OSDG+ChineseLLM (hybrid-20260329)": str(MODELS_DIR / "sdg-finetuned/sdg-hybrid_enhanced-20260329_154654"),
    "ST OSDG+AidData variants (variant-20260417)": str(MODELS_DIR / "sdg-finetuned/sdg-variant-finetuned-20260417_085525"),
}

BERT_MODELS = {
    "BERT baseline (sadickam/sdgBERT)": "sadickam/sdgBERT",
    "BERT current (multilabel-20260420)": str(MODELS_DIR / "sdg-bert-multilabel/sdg-bert-multilabel-20260420_120423"),
}


def optimize_thresholds_for_model(scores: np.ndarray, labels: np.ndarray) -> Dict[int, float]:
    """Optimize per-SDG thresholds on weightopt split."""
    thresholds = {}
    support = labels.sum(axis=0).astype(int)
    for sdg_idx in range(NUM_SDGS):
        sdg_num = sdg_idx + 1
        opt = optimize_sdg_threshold(scores, labels, sdg_idx, int(support[sdg_idx]))
        if opt["final"]["f1"] == 0 and opt["final"]["threshold"] >= 0.99:
            thresholds[sdg_num] = 1.0
        else:
            thresholds[sdg_num] = opt["final"]["threshold"]
    return thresholds


def compute_aiddata_accuracy(scores: np.ndarray, labels: np.ndarray, thresholds: Dict[int, float]) -> Dict:
    """Compute AidData multi-label accuracy: Hamming acc + sample F1."""
    y_pred = np.zeros_like(labels, dtype=np.int32)
    for sdg_num in range(1, 18):
        y_pred[:, sdg_num - 1] = (scores[:, sdg_num - 1] >= thresholds[sdg_num]).astype(int)
    for i in range(len(y_pred)):
        if y_pred[i].sum() == 0:
            y_pred[i, scores[i].argmax()] = 1

    hamming_acc = float((y_pred == labels).mean())

    sample_f1s = []
    for i in range(len(y_pred)):
        tp = int((y_pred[i] & labels[i]).sum())
        fp = int((y_pred[i] & ~labels[i]).sum())
        fn = int((~y_pred[i] & labels[i]).sum())
        if tp + fp + fn == 0:
            sample_f1s.append(1.0)
        else:
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            sample_f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0)
    sample_f1 = float(np.mean(sample_f1s))

    return {"hamming_acc": hamming_acc, "sample_f1": sample_f1}


def evaluate_model(
    name: str,
    scores: np.ndarray,
    labels: np.ndarray,
    thresholds: Dict[int, float],
    osdg_labels: List[int],
    osdg_scores: np.ndarray,
    aid_labels: np.ndarray = None,
    aid_scores: np.ndarray = None,
) -> Dict:
    """Evaluate a model with optimized thresholds."""
    metrics = compute_macro_f1(scores, labels, thresholds)
    osdg_acc = evaluate_osdg_top1_accuracy(osdg_scores, osdg_labels) if osdg_labels else None

    result = {
        "name": name,
        "macro_f1": float(metrics["macro_f1"]),
        "macro_precision": float(metrics["macro_precision"]),
        "macro_recall": float(metrics["macro_recall"]),
        "avg_fp_rate": float(metrics["avg_fp_rate"]),
        "osdg_accuracy": float(osdg_acc) if osdg_acc else None,
        "aiddata_hamming": None,
        "aiddata_sample_f1": None,
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

    if aid_labels is not None and aid_scores is not None:
        aid_metrics = compute_aiddata_accuracy(aid_scores, aid_labels, thresholds)
        result["aiddata_hamming"] = aid_metrics["hamming_acc"]
        result["aiddata_sample_f1"] = aid_metrics["sample_f1"]

    return result


def main():
    parser = argparse.ArgumentParser(description="Benchmark all fine-tuned models")
    parser.add_argument("--device", default=None, help="Force device (cpu/mps/cuda)")
    parser.add_argument("--skip-st", action="store_true", help="Skip ST models")
    parser.add_argument("--skip-bert", action="store_true", help="Skip BERT models")
    parser.add_argument("--output", default="results/model_comparison.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    # Load data
    splits = load_splits()
    aid_wo = splits["aid_wo"]
    aid_oot = splits["aid_oot"]
    osdg_wo = splits["osdg_wo"]
    osdg_oot = splits["osdg_oot"]

    combined_wo_labels = np.vstack([aid_wo["labels"], osdg_labels_to_multi(osdg_wo["labels"])])
    combined_wo_texts = aid_wo["texts"] + osdg_wo["texts"]
    combined_oot_labels = np.vstack([aid_oot["labels"], osdg_labels_to_multi(osdg_oot["labels"])])
    combined_oot_texts = aid_oot["texts"] + osdg_oot["texts"]

    all_results = {}

    # === ST MODELS ===
    if not args.skip_st:
        print("\n" + "=" * 80)
        print("  BENCHMARKING SENTENCE TRANSFORMER MODELS")
        print("=" * 80)

        for name, model_path in ST_MODELS.items():
            print(f"\n--- {name} ---")
            print(f"    Model: {model_path}")

            # Check if model exists (local path)
            if model_path != "all-MiniLM-L6-v2" and not Path(model_path).exists():
                print(f"    SKIPPED: model not found at {model_path}")
                continue

            try:
                engine = AlignmentEngine(model_name=model_path)
            except Exception as e:
                print(f"    SKIPPED: failed to load model: {e}")
                continue

            t0 = time.time()
            wo_scores = precompute_st_scores(engine, combined_wo_texts)
            oot_scores = precompute_st_scores(engine, combined_oot_texts)
            elapsed = time.time() - t0
            print(f"    Score computation: {elapsed:.1f}s")

            # Optimize thresholds on weightopt
            print("    Optimizing thresholds...")
            thresholds = optimize_thresholds_for_model(wo_scores, combined_wo_labels)

            # Evaluate on OOS
            n_aid = len(aid_oot["texts"])
            aid_oot_sub = oot_scores[:n_aid]
            osdg_oot_sub = oot_scores[n_aid:]
            result = evaluate_model(
                name, oot_scores, combined_oot_labels, thresholds,
                osdg_oot["labels"], osdg_oot_sub,
                aid_oot["labels"], aid_oot_sub,
            )
            result["model_path"] = model_path
            result["score_time_s"] = elapsed
            all_results[name] = result

            aid_h = f"{result['aiddata_hamming']:.4f}" if result['aiddata_hamming'] else "N/A"
            aid_f = f"{result['aiddata_sample_f1']:.4f}" if result['aiddata_sample_f1'] else "N/A"
            print(f"    Macro F1: {result['macro_f1']:.4f}  "
                  f"P: {result['macro_precision']:.4f}  "
                  f"R: {result['macro_recall']:.4f}  "
                  f"OSDG acc: {result['osdg_accuracy']:.4f}  "
                  f"AidData Hamm: {aid_h}  AidData sF1: {aid_f}")

    # === BERT MODELS ===
    if not args.skip_bert:
        print("\n" + "=" * 80)
        print("  BENCHMARKING sdgBERT MODELS")
        print("=" * 80)

        for name, model_path in BERT_MODELS.items():
            print(f"\n--- {name} ---")
            print(f"    Model: {model_path}")

            try:
                bert = SDGBERTClassifier(model_name=model_path, device=args.device)
                print(f"    Multi-label: {bert.is_multilabel}, num_labels: {bert.num_labels}")
            except Exception as e:
                print(f"    SKIPPED: failed to load model: {e}")
                continue

            t0 = time.time()
            wo_scores = precompute_sdg_bert_scores(bert, combined_wo_texts)
            oot_scores = precompute_sdg_bert_scores(bert, combined_oot_texts)
            elapsed = time.time() - t0
            print(f"    Score computation: {elapsed:.1f}s")

            # Optimize thresholds on weightopt
            print("    Optimizing thresholds...")
            thresholds = optimize_thresholds_for_model(wo_scores, combined_wo_labels)

            # Evaluate on OOS
            n_aid = len(aid_oot["texts"])
            aid_oot_sub = oot_scores[:n_aid]
            osdg_oot_sub = oot_scores[n_aid:]
            result = evaluate_model(
                name, oot_scores, combined_oot_labels, thresholds,
                osdg_oot["labels"], osdg_oot_sub,
                aid_oot["labels"], aid_oot_sub,
            )
            result["model_path"] = model_path
            result["is_multilabel"] = bert.is_multilabel
            result["num_labels"] = bert.num_labels
            result["score_time_s"] = elapsed
            all_results[name] = result

            aid_h = f"{result['aiddata_hamming']:.4f}" if result['aiddata_hamming'] else "N/A"
            aid_f = f"{result['aiddata_sample_f1']:.4f}" if result['aiddata_sample_f1'] else "N/A"
            print(f"    Macro F1: {result['macro_f1']:.4f}  "
                  f"P: {result['macro_precision']:.4f}  "
                  f"R: {result['macro_recall']:.4f}  "
                  f"OSDG acc: {result['osdg_accuracy']:.4f}  "
                  f"AidData Hamm: {aid_h}  AidData sF1: {aid_f}")

    # === PRINT COMPARISON TABLES ===

    # Sort results by Macro F1
    sorted_results = sorted(all_results.items(), key=lambda x: x[1]["macro_f1"], reverse=True)

    print("\n" + "=" * 138)
    print("  MODEL COMPARISON — OUT-OF-SAMPLE RESULTS (ranked by Macro F1)")
    print("=" * 138)
    print(f"\n  {'#':<3} {'Model':<52} {'Macro F1':>10} {'Macro P':>10} {'Macro R':>10} "
          f"{'Avg FP':>8} {'OSDG Acc':>10} {'Aid Hamm':>10} {'Aid sF1':>10}")
    print(f"  {'-'*3} {'-'*52} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")

    for rank, (name, result) in enumerate(sorted_results, 1):
        osdg_str = f"{result['osdg_accuracy']:.4f}" if result['osdg_accuracy'] else "N/A"
        aid_h = f"{result['aiddata_hamming']:.4f}" if result['aiddata_hamming'] else "N/A"
        aid_f = f"{result['aiddata_sample_f1']:.4f}" if result['aiddata_sample_f1'] else "N/A"
        print(f"  {rank:<3} {name:<52} {result['macro_f1']:>10.4f} "
              f"{result['macro_precision']:>10.4f} {result['macro_recall']:>10.4f} "
              f"{result['avg_fp_rate']:>8.4f} {osdg_str:>10} {aid_h:>10} {aid_f:>10}")

    # Per-SDG comparison table
    print("\n" + "=" * 120)
    print("  PER-SDG F1 COMPARISON — OUT-OF-SAMPLE")
    print("=" * 120)

    model_names = [name for name, _ in sorted_results]
    header = f"  {'SDG':<4} {'Name':<24} " + " ".join(f"{n[:10]:>10}" for n in model_names)
    print(header)
    print(f"  {'-'*4} {'-'*24} " + " ".join(f"{'-'*10}" for _ in model_names))

    for sdg in range(1, 18):
        name = SDG_NAMES[sdg]
        row = f"  {sdg:<4} {name:<24} "
        for mname in model_names:
            f1 = all_results[mname]["per_sdg"].get(str(sdg), {}).get("f1", 0)
            row += f"{f1:>10.3f} "
        print(row)

    # Macro F1 row
    print(f"  {'-'*4} {'-'*24} " + " ".join(f"{'-'*10}" for _ in model_names))
    row = f"  {'':4} {'MACRO F1':<24} "
    for mname in model_names:
        row += f"{all_results[mname]['macro_f1']:>10.4f} "
    print(row)

    # Problem SDGs summary per model
    print(f"\n  Problem SDGs (OOS F1 < 0.5) per model:")
    for name in model_names:
        problems = [(sdg, all_results[name]["per_sdg"][str(sdg)]["f1"])
                     for sdg in range(1, 18) if all_results[name]["per_sdg"][str(sdg)]["f1"] < 0.5]
        if problems:
            pstr = ", ".join(f"SDG{s}({f:.2f})" for s, f in problems)
            print(f"    {name[:50]}: {pstr}")
        else:
            print(f"    {name[:50]}: None")

    # Save results
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


if __name__ == "__main__":
    main()