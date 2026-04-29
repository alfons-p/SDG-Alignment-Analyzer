#!/usr/bin/env python3
"""Benchmark SDG alignment thresholds across all three modes.

Compares current optimized models against baselines:
  - ST current: voyager205/sdg-finetuned-enhanced (5-variant with targets)
  - ST baseline: all-MiniLM-L6-v2 (original, no SDG fine-tuning)
  - sdgBERT current: fine-tuned multi-label (17-class sigmoid)
  - sdgBERT baseline: sadickam/sdgBERT (16-class softmax, no SDG 17)

Evaluates on both weightopt and out-of-sample splits from AidData + OSDG.

Usage:
    python scripts/benchmark_thresholds.py
    python scripts/benchmark_thresholds.py --device cpu
    python scripts/benchmark_thresholds.py --skip-baselines
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import torch

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT
from src.config.threshold_config import get_all_thresholds, THRESHOLD_CONFIG

# Import from optimizer using importlib to avoid scripts/__init__.py
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
FP_CEILING = _opt.FP_CEILING
COARSE_STEP = _opt.COARSE_STEP
FINE_STEP = _opt.FINE_STEP

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


def evaluate_mode(
    mode: str,
    scores: np.ndarray,
    labels: np.ndarray,
    thresholds: Dict[int, float],
    osdg_labels: List[int] = None,
    osdg_scores: np.ndarray = None,
    split_name: str = "validation",
) -> Dict:
    """Evaluate one mode with given thresholds. Returns per-SDG + macro metrics."""
    metrics = compute_macro_f1(scores, labels, thresholds)

    result = {
        "mode": mode,
        "split": split_name,
        "macro_f1": metrics["macro_f1"],
        "macro_precision": metrics["macro_precision"],
        "macro_recall": metrics["macro_recall"],
        "avg_fp_rate": metrics["avg_fp_rate"],
        "per_sdg": metrics["per_sdg"],
    }

    # OSDG top-1 accuracy
    if osdg_labels is not None and osdg_scores is not None:
        result["osdg_accuracy"] = evaluate_osdg_top1_accuracy(osdg_scores, osdg_labels)

    return result


def optimize_thresholds_for_scores(
    wo_scores: np.ndarray,
    wo_labels: np.ndarray,
) -> Dict[int, float]:
    """Optimize per-SDG thresholds on the weightopt split.

    Used for baseline models that don't have pre-optimized thresholds.
    Same two-pass sweep as optimize_thresholds.py.
    """
    thresholds = {}
    support = wo_labels.sum(axis=0).astype(int)
    for sdg_idx in range(NUM_SDGS):
        sdg_num = sdg_idx + 1
        opt = optimize_sdg_threshold(wo_scores, wo_labels, sdg_idx, int(support[sdg_idx]))
        # For 16-class sdgBERT baseline, SDG 17 scores are all 0 — use high threshold
        if opt["final"]["f1"] == 0 and opt["final"]["threshold"] >= 0.99:
            thresholds[sdg_num] = 1.0  # Impossible threshold — never predict
        else:
            thresholds[sdg_num] = opt["final"]["threshold"]

    return thresholds


def print_benchmark_report(results: Dict, mode: str):
    """Print a detailed benchmark table for one mode."""
    val = results.get("validation", {})
    oos = results.get("outofsample", {})

    val_per = val.get("per_sdg", {})
    oos_per = oos.get("per_sdg", {})

    mode_display = mode.upper() if mode != "sdgbert" else "sdgBERT"

    print(f"\n{'='*90}")
    print(f"  {mode_display} MODE — BENCHMARK RESULTS")
    print(f"{'='*90}")

    # Macro summary
    print(f"\n  {'Split':<15} {'Macro F1':>10} {'Macro P':>10} {'Macro R':>10} {'Avg FP':>10}", end="")
    if "osdg_accuracy" in val or "osdg_accuracy" in oos:
        print(f" {'OSDG acc':>10}")
    else:
        print()

    for split_name, data in [("Weightopt", val), ("Out-of-sample", oos)]:
        if not data:
            continue
        print(f"  {split_name:<15} {data['macro_f1']:>10.4f} {data['macro_precision']:>10.4f} "
              f"{data['macro_recall']:>10.4f} {data['avg_fp_rate']:>10.4f}", end="")
        if "osdg_accuracy" in data:
            acc = data["osdg_accuracy"]
            flag = "" if acc >= 0.876 else " ***"
            print(f" {acc:>10.4f}{flag}")
        else:
            print()

    # Per-SDG table
    print(f"\n  {'SDG':<4} {'Name':<24} {'t':>6} "
          f"{'Val F1':>7} {'Val P':>7} {'Val R':>7} {'Val FP':>7} "
          f"{'OOS F1':>7} {'OOS P':>7} {'OOS R':>7} {'OOS FP':>7} {'n':>5}")
    print(f"  {'-'*4} {'-'*24} {'-'*6} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*5}")

    thresholds = get_all_thresholds(mode)

    for sdg in range(1, 18):
        t = thresholds[sdg]
        v = val_per.get(sdg, {})
        o = oos_per.get(sdg, {})
        name = SDG_NAMES.get(sdg, "")
        support = v.get("support", o.get("support", 0))

        vf1 = v.get("f1", 0)
        vp = v.get("precision", 0)
        vr = v.get("recall", 0)
        vfp = v.get("fp_rate", 0)

        of1 = o.get("f1", 0)
        op = o.get("precision", 0)
        or_ = o.get("recall", 0)
        ofp = o.get("fp_rate", 0)

        # Flag low support or high FP
        flags = ""
        if support < 50:
            flags = " [LOW]"
        elif vfp > 0.10 or ofp > 0.10:
            flags = " [HIGH FP]"

        print(f"  {sdg:<4} {name:<24} {t:>6.3f} "
              f"{vf1:>7.3f} {vp:>7.3f} {vr:>7.3f} {vfp:>7.3f} "
              f"{of1:>7.3f} {op:>7.3f} {or_:>7.3f} {ofp:>7.3f} {support:>5}{flags}")

    # Problem SDGs summary
    print(f"\n  Problem SDGs (OOS F1 < 0.5):")
    problems = []
    for sdg in range(1, 18):
        o = oos_per.get(sdg, {})
        if o.get("f1", 1) < 0.5:
            problems.append((sdg, o.get("f1", 0), o.get("fp_rate", 0)))
    if problems:
        for sdg, f1, fp in problems:
            print(f"    SDG {sdg:2d} ({SDG_NAMES[sdg]}): F1={f1:.3f}, FP={fp:.3f}")
    else:
        print("    None — all SDGs above 0.5 F1")

    print(f"{'='*90}")


def print_comparison_table(all_results: Dict):
    """Print a side-by-side comparison of all modes including baselines."""
    # Determine which result keys are available
    modes = ["st", "sdgbert", "hybrid"]
    baselines = [k for k in all_results if k.startswith("baseline_")]
    all_modes = modes + baselines

    # Mode display names
    display_names = {
        "st": "ST (current)",
        "sdgbert": "BERT (current)",
        "hybrid": "Hybrid",
        "baseline_st": "ST (baseline)",
        "baseline_bert": "BERT (baseline)",
        "baseline_hybrid": "Hybrid (baseline)",
    }

    col_width = 8
    n_modes = len([m for m in all_modes if m in all_results])
    total_width = 4 + 24 + (col_width * n_modes) + 8

    print(f"\n{'='*max(100, total_width)}")
    print(f"  FULL COMPARISON — OUT-OF-SAMPLE F1 SCORES")
    print(f"{'='*max(100, total_width)}")

    # Header
    header = f"  {'SDG':<4} {'Name':<24} "
    for m in all_modes:
        if m in all_results:
            header += f"{display_names.get(m, m):>{col_width}} "
    print(header)
    sep = f"  {'-'*4} {'-'*24} "
    for m in all_modes:
        if m in all_results:
            sep += f"{'-'*col_width} "
    print(sep)

    # Per-SDG rows
    for sdg in range(1, 18):
        name = SDG_NAMES.get(sdg, "")
        row = f"  {sdg:<4} {name:<24} "
        best_f1 = 0
        best_mode = ""
        for m in all_modes:
            if m not in all_results:
                continue
            f1 = all_results[m].get("outofsample", {}).get("per_sdg", {}).get(sdg, {}).get("f1", 0)
            row += f"{f1:>{col_width}.3f} "
            if f1 > best_f1:
                best_f1 = f1
                best_mode = display_names.get(m, m)
        print(row)

    # Macro summary
    print(sep)
    for metric_key, metric_name in [("macro_f1", "Macro F1"), ("avg_fp_rate", "Avg FP Rate")]:
        row = f"  {'':4} {metric_name:<24} "
        for m in all_modes:
            if m not in all_results:
                continue
            v = all_results[m].get("outofsample", {}).get(metric_key, 0)
            row += f"{v:>{col_width}.4f} "
        print(row)

    # OSDG accuracy
    row = f"  {'':4} {'OSDG accuracy':<24} "
    for m in all_modes:
        if m not in all_results:
            continue
        acc = all_results[m].get("outofsample", {}).get("osdg_accuracy", 0)
        if acc:
            flag = " *" if acc < 0.876 else ""
            row += f"{acc:>{col_width-1}.3f}{flag} "
        else:
            row += f"{'N/A':>{col_width}} "
    print(row)

    print(f"\n  * = below OSDG baseline (0.876)")
    print(f"  ST (current)  = voyager205/sdg-finetuned-enhanced (5-variant + targets)")
    print(f"  ST (baseline) = all-MiniLM-L6-v2 (original, no SDG fine-tuning)")
    print(f"  BERT (current)  = fine-tuned multi-label 17-class sigmoid")
    print(f"  BERT (baseline) = sadickam/sdgBERT 16-class softmax (no SDG 17)")
    print(f"{'='*max(100, total_width)}")


def print_improvement_table(all_results: Dict):
    """Print improvement from baselines to current models."""
    print(f"\n{'='*90}")
    print(f"  IMPROVEMENT OVER BASELINES — OUT-OF-SAMPLE F1 DELTA")
    print(f"{'='*90}")

    st_base = all_results.get("baseline_st", {}).get("outofsample", {}).get("per_sdg", {})
    st_curr = all_results.get("st", {}).get("outofsample", {}).get("per_sdg", {})
    bert_base = all_results.get("baseline_bert", {}).get("outofsample", {}).get("per_sdg", {})
    bert_curr = all_results.get("sdgbert", {}).get("outofsample", {}).get("per_sdg", {})

    has_st_base = bool(st_base)
    has_bert_base = bool(bert_base)

    header = f"  {'SDG':<4} {'Name':<24} "
    if has_st_base:
        header += f"{'ST base':>8} {'ST now':>8} {'Δ':>7} "
    if has_bert_base:
        header += f"{'BERT base':>9} {'BERT now':>9} {'Δ':>7}"
    print(header)

    sep = f"  {'-'*4} {'-'*24} "
    if has_st_base:
        sep += f"{'-'*8} {'-'*8} {'-'*7} "
    if has_bert_base:
        sep += f"{'-'*9} {'-'*9} {'-'*7}"
    print(sep)

    for sdg in range(1, 18):
        name = SDG_NAMES.get(sdg, "")
        row = f"  {sdg:<4} {name:<24} "

        if has_st_base:
            sb = st_base.get(sdg, {}).get("f1", 0)
            sc = st_curr.get(sdg, {}).get("f1", 0)
            delta = sc - sb
            sign = "+" if delta >= 0 else ""
            row += f"{sb:>8.3f} {sc:>8.3f} {sign}{delta:>6.3f} "

        if has_bert_base:
            bb = bert_base.get(sdg, {}).get("f1", 0)
            bc = bert_curr.get(sdg, {}).get("f1", 0)
            delta = bc - bb
            sign = "+" if delta >= 0 else ""
            row += f"{bb:>9.3f} {bc:>9.3f} {sign}{delta:>6.3f}"

        print(row)

    # Macro summary
    print(sep)
    if has_st_base:
        sb = all_results.get("baseline_st", {}).get("outofsample", {}).get("macro_f1", 0)
        sc = all_results.get("st", {}).get("outofsample", {}).get("macro_f1", 0)
        delta = sc - sb
        sign = "+" if delta >= 0 else ""
        print(f"  {'':4} {'Macro F1':<24} {sb:>8.4f} {sc:>8.4f} {sign}{delta:>6.4f}", end="")
    if has_bert_base:
        bb = all_results.get("baseline_bert", {}).get("outofsample", {}).get("macro_f1", 0)
        bc = all_results.get("sdgbert", {}).get("outofsample", {}).get("macro_f1", 0)
        delta = bc - bb
        sign = "+" if delta >= 0 else ""
        print(f"  {bb:>9.4f} {bc:>9.4f} {sign}{delta:>6.4f}", end="")
    if not has_st_base:
        print("  (no ST baseline)", end="")
    print()

    print(f"{'='*90}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark SDG alignment thresholds")
    parser.add_argument("--sdg-bert-model", default=None,
                        help="Path to fine-tuned sdgBERT model (default: local fine-tuned)")
    parser.add_argument("--device", default=None, help="Force device (cpu/mps/cuda)")
    parser.add_argument("--skip-st", action="store_true", help="Skip ST mode")
    parser.add_argument("--skip-bert", action="store_true", help="Skip sdgBERT mode")
    parser.add_argument("--skip-hybrid", action="store_true", help="Skip Hybrid mode")
    parser.add_argument("--skip-baselines", action="store_true",
                        help="Skip baseline model comparisons (faster)")
    parser.add_argument("--output", default="results/benchmark_thresholds.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    # Load data
    splits = load_splits()

    # Initialize current engines
    print("\nInitializing Sentence Transformer engine...")
    st_engine = AlignmentEngine() if not args.skip_st else None

    sdg_bert = None
    if not args.skip_bert or not args.skip_hybrid:
        sdg_bert = SDGBERTClassifier(model_name=args.sdg_bert_model, device=args.device)

    # Initialize baseline engines
    baseline_st_engine = None
    baseline_bert = None
    if not args.skip_baselines:
        if not args.skip_st:
            print("\nInitializing baseline ST engine (all-MiniLM-L6-v2)...")
            baseline_st_engine = AlignmentEngine(model_name="all-MiniLM-L6-v2")
        if not args.skip_bert:
            print("\nInitializing baseline sdgBERT (sadickam/sdgBERT)...")
            baseline_bert = SDGBERTClassifier(
                model_name=SDGBERTClassifier.FALLBACK_MODEL,
                device=args.device,
            )

    # Prepare combined labels
    aid_wo = splits["aid_wo"]
    aid_oot = splits["aid_oot"]
    osdg_wo = splits["osdg_wo"]
    osdg_oot = splits["osdg_oot"]

    combined_wo_labels = np.vstack([aid_wo["labels"], osdg_labels_to_multi(osdg_wo["labels"])])
    combined_wo_texts = aid_wo["texts"] + osdg_wo["texts"]
    combined_oot_labels = np.vstack([aid_oot["labels"], osdg_labels_to_multi(osdg_oot["labels"])])
    combined_oot_texts = aid_oot["texts"] + osdg_oot["texts"]

    # --- Pre-compute current model scores ---
    st_wo_scores = st_oot_scores = None
    if not args.skip_st:
        print("\n--- Pre-computing ST scores (current) ---")
        st_wo_scores = precompute_st_scores(st_engine, combined_wo_texts)
        st_oot_scores = precompute_st_scores(st_engine, combined_oot_texts)

    bert_wo_scores = bert_oot_scores = None
    if sdg_bert is not None:
        print("\n--- Pre-computing sdgBERT scores (current) ---")
        bert_wo_scores = precompute_sdg_bert_scores(sdg_bert, combined_wo_texts)
        bert_oot_scores = precompute_sdg_bert_scores(sdg_bert, combined_oot_texts)

    hybrid_wo_scores = hybrid_oot_scores = None
    if st_wo_scores is not None and bert_wo_scores is not None and not args.skip_hybrid:
        print("\n--- Computing Hybrid scores (current) ---")
        hybrid_wo_scores = compute_hybrid_scores(st_wo_scores, bert_wo_scores)
        hybrid_oot_scores = compute_hybrid_scores(st_oot_scores, bert_oot_scores)

    # --- Pre-compute baseline model scores ---
    baseline_st_wo = baseline_st_oot = None
    if baseline_st_engine is not None:
        print("\n--- Pre-computing ST scores (baseline: all-MiniLM-L6-v2) ---")
        baseline_st_wo = precompute_st_scores(baseline_st_engine, combined_wo_texts)
        baseline_st_oot = precompute_st_scores(baseline_st_engine, combined_oot_texts)

    baseline_bert_wo = baseline_bert_oot = None
    if baseline_bert is not None:
        print("\n--- Pre-computing sdgBERT scores (baseline: sadickam/sdgBERT) ---")
        baseline_bert_wo = precompute_sdg_bert_scores(baseline_bert, combined_wo_texts)
        baseline_bert_oot = precompute_sdg_bert_scores(baseline_bert, combined_oot_texts)

    baseline_hybrid_wo = baseline_hybrid_oot = None
    if baseline_st_wo is not None and baseline_bert_wo is not None and not args.skip_hybrid:
        print("\n--- Computing Hybrid scores (baseline) ---")
        baseline_hybrid_wo = compute_hybrid_scores(baseline_st_wo, baseline_bert_wo)
        baseline_hybrid_oot = compute_hybrid_scores(baseline_st_oot, baseline_bert_oot)

    # --- Evaluate all modes ---
    all_results = {}

    # Current models — use threshold_config.py thresholds
    current_modes = {
        "st": (st_wo_scores, st_oot_scores),
        "sdgbert": (bert_wo_scores, bert_oot_scores),
        "hybrid": (hybrid_wo_scores, hybrid_oot_scores),
    }

    for mode, (wo_scores, oot_scores) in current_modes.items():
        if wo_scores is None:
            continue
        thresholds = get_all_thresholds(mode)
        print(f"\n--- Evaluating {mode} mode ---")

        osdg_wo_sub = wo_scores[len(aid_wo["texts"]):]
        osdg_oot_sub = oot_scores[len(aid_oot["texts"]):]

        all_results[mode] = {
            "validation": evaluate_mode(
                mode, wo_scores, combined_wo_labels, thresholds,
                osdg_labels=osdg_wo["labels"], osdg_scores=osdg_wo_sub,
                split_name="weightopt",
            ),
            "outofsample": evaluate_mode(
                mode, oot_scores, combined_oot_labels, thresholds,
                osdg_labels=osdg_oot["labels"], osdg_scores=osdg_oot_sub,
                split_name="outofsample",
            ),
            "thresholds": {int(k): float(v) for k, v in thresholds.items()},
        }

    # Baseline models — optimize thresholds on weightopt split
    baseline_modes = {
        "baseline_st": (baseline_st_wo, baseline_st_oot),
        "baseline_bert": (baseline_bert_wo, baseline_bert_oot),
        "baseline_hybrid": (baseline_hybrid_wo, baseline_hybrid_oot),
    }

    for mode, (wo_scores, oot_scores) in baseline_modes.items():
        if wo_scores is None:
            continue
        print(f"\n--- Optimizing thresholds for {mode} ---")
        thresholds = optimize_thresholds_for_scores(wo_scores, combined_wo_labels)
        print(f"--- Evaluating {mode} mode ---")

        osdg_wo_sub = wo_scores[len(aid_wo["texts"]):]
        osdg_oot_sub = oot_scores[len(aid_oot["texts"]):]

        all_results[mode] = {
            "validation": evaluate_mode(
                mode, wo_scores, combined_wo_labels, thresholds,
                osdg_labels=osdg_wo["labels"], osdg_scores=osdg_wo_sub,
                split_name="weightopt",
            ),
            "outofsample": evaluate_mode(
                mode, oot_scores, combined_oot_labels, thresholds,
                osdg_labels=osdg_oot["labels"], osdg_scores=osdg_oot_sub,
                split_name="outofsample",
            ),
            "thresholds": {int(k): float(v) for k, v in thresholds.items()},
        }

    # --- Print reports ---
    for mode in ["st", "sdgbert", "hybrid"]:
        if mode in all_results:
            print_benchmark_report(all_results[mode], mode)

    print_comparison_table(all_results)

    if not args.skip_baselines:
        print_improvement_table(all_results)

    # Config version info
    print(f"\n  Config version: {THRESHOLD_CONFIG['version']} ({THRESHOLD_CONFIG['date']})")
    print(f"  Models: ST={st_engine.model_name if st_engine else 'skipped'}, "
          f"BERT={sdg_bert.model_name if sdg_bert else 'skipped'}")
    if not args.skip_baselines:
        print(f"  Baselines: ST={baseline_st_engine.model_name if baseline_st_engine else 'skipped'}, "
              f"BERT={baseline_bert.model_name if baseline_bert else 'skipped'}")

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