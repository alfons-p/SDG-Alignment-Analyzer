#!/usr/bin/env python3
"""Benchmark SDG Alignment Engines against AidData Chinese Development Finance Dataset.

Loads the AidData Excel file with ground-truth SDG categorizations, runs both
ST-only and Hybrid alignment engines, and produces a comprehensive benchmarking
report comparing predictions against ground truth.

Usage:
    python scripts/benchmark_aiddata.py [--max-samples 1000] [--output-dir results/benchmark_aiddata/]
"""

import sys
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.alignment_engine import AlignmentEngine
from src.hybrid_alignment_engine import HybridAlignmentEngine
from src.config.threshold_config import get_all_thresholds, get_threshold
from src.config.sdg_definitions import SDG_DEFINITIONS
from src.config.sdg_target_definitions import SDG_TARGET_DEFINITIONS

XLSX_PATH = Path("data/external/30015124/Chinese_Development_Finance_SDG_Categorizations_2000-2021.xlsx")
SDG_COLS = [f"SDG{i}" for i in range(1, 18)]
SDG_NAMES = {i: SDG_DEFINITIONS[i]["name"] for i in range(1, 18)}


def load_aiddata(xlsx_path: Path, worksheet: str, max_samples: Optional[int] = None) -> pd.DataFrame:
    """Load Excel worksheet with optional stratified sampling.

    Stratified sampling preserves SDG label distribution to ensure rare SDGs
    are represented in the sample.
    """
    print(f"\nLoading worksheet '{worksheet}' from {xlsx_path}...")
    df = pd.read_excel(xlsx_path, sheet_name=worksheet)

    # Drop rows without Description or all SDG columns NaN
    df = df.dropna(subset=["Description"])
    df = df[df["Description"].str.strip() != ""]
    df = df.dropna(subset=SDG_COLS, how="all")

    # Ensure SDG columns are integers
    for col in SDG_COLS:
        df[col] = df[col].fillna(0).astype(int)

    total_rows = len(df)
    print(f"  Valid rows: {total_rows}")

    if max_samples and max_samples < total_rows:
        df = _stratified_sample(df, max_samples)
        print(f"  Stratified sample: {len(df)} rows")

    # Compute description word counts
    df["_word_count"] = df["Description"].str.split().str.len()

    return df


def _stratified_sample(df: pd.DataFrame, max_samples: int) -> pd.DataFrame:
    """Stratified sample preserving SDG label distribution.

    Groups rows by their SDG label set, then samples proportionally from
    each group. Rare groups get all their rows included.
    """
    # Create a label signature for each row (tuple of SDGs present)
    def label_signature(row):
        return tuple(i for i in range(1, 18) if row[f"SDG{i}"] == 1)

    df = df.copy()
    df["_signature"] = df.apply(label_signature, axis=1)

    # Group by label signature
    grouped = df.groupby("_signature")

    # Calculate proportional sample sizes
    sampled_dfs = []
    for signature, group in grouped:
        group_size = len(group)
        proportion = group_size / len(df)
        n_samples = max(1, int(round(proportion * max_samples)))

        if n_samples >= group_size:
            sampled_dfs.append(group)
        else:
            sampled_dfs.append(group.sample(n=n_samples, random_state=42))

    result = pd.concat(sampled_dfs).drop(columns=["_signature"])
    # Shuffle to avoid ordering bias
    result = result.sample(frac=1, random_state=42).reset_index(drop=True)
    return result


def compute_sdg_distribution(df: pd.DataFrame) -> Dict[str, float]:
    """Compute SDG prevalence in a DataFrame."""
    dist = {}
    for i in range(1, 18):
        col = f"SDG{i}"
        if col in df.columns:
            dist[str(i)] = round(df[col].mean(), 4)
    return dist


def compute_label_stats(labels: np.ndarray) -> Dict[str, Any]:
    """Compute label cardinality, density, and distribution.

    Args:
        labels: (N, 17) binary array where columns are SDG 1-17
    """
    counts_per_row = labels.sum(axis=1)
    cardinality = float(counts_per_row.mean())
    density = round(cardinality / 17, 4)

    # Distribution: count of rows with 0, 1, 2, 3, 4, 5+ SDGs
    dist = {}
    for n in range(5):
        dist[str(n)] = int((counts_per_row == n).sum())
    dist["5+"] = int((counts_per_row >= 5).sum())

    return {"cardinality": round(cardinality, 2), "density": density, "distribution": dist}


def run_engine(
    engine_mode: str,
    texts: List[str],
    df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Run alignment engine and return (predictions, raw_scores, config_info).

    Args:
        engine_mode: 'st', 'hybrid', 'st_target_boost', or 'hybrid_target_boost'
        texts: List of Description texts
        df: DataFrame with ground truth SDG columns

    Returns:
        predictions: (N, 17) binary array of is_aligned predictions
        raw_scores: (N, 17) array of alignment scores
        config_info: dict with engine configuration details
    """
    use_target_boost = "target_boost" in engine_mode
    base_mode = "st" if "st" in engine_mode else "hybrid"
    thresholds = get_all_thresholds(base_mode)

    if base_mode == "st":
        print(f"\nInitializing ST-only engine (target_boost={use_target_boost})...")
        engine = AlignmentEngine()
    else:
        print(f"\nInitializing Hybrid engine (ST + sdgBERT, target_boost={use_target_boost})...")
        engine = HybridAlignmentEngine(use_sdg_bert=True, ensemble_mode="weighted")

    # Get model info
    if base_mode == "st":
        config_info = {
            "mode": "sentence_transformer",
            "model": engine.model_name if hasattr(engine, 'model_name') else "unknown",
            "target_boost": use_target_boost,
            "thresholds": {str(k): v for k, v in thresholds.items()},
        }
    else:
        model_info = engine.get_model_info()
        config_info = {
            "mode": "hybrid",
            "st_model": model_info.get("sentence_transformer_model", "unknown"),
            "sdg_bert_model": model_info.get("sdg_bert_model", "unknown"),
            "sdg_bert_loaded": model_info.get("sdg_bert_loaded", False),
            "ensemble_mode": model_info.get("ensemble_mode", "weighted"),
            "target_boost": use_target_boost,
            "thresholds": {str(k): v for k, v in thresholds.items()},
        }

    # Batch process using align_activities
    activities = [{"text": t} for t in texts]
    print(f"Running {engine_mode} alignment on {len(texts)} texts...")

    start_time = time.time()
    results = engine.align_activities(activities, show_progress=True, target_boost=use_target_boost)
    elapsed = time.time() - start_time
    print(f"  Completed in {elapsed:.1f}s ({len(texts)/elapsed:.1f} texts/sec)")

    # Extract predictions and raw scores
    n = len(results)
    predictions = np.zeros((n, 17), dtype=int)
    raw_scores = np.zeros((n, 17), dtype=float)

    for i, result in enumerate(results):
        for sdg_num in range(1, 18):
            score_data = result["sdg_scores"][sdg_num]
            raw_scores[i, sdg_num - 1] = score_data["score"]
            # Use the engine's is_aligned decision (which respects per-SDG thresholds)
            predictions[i, sdg_num - 1] = 1 if score_data["is_aligned"] else 0

    config_info["runtime_seconds"] = round(elapsed, 1)
    config_info["texts_per_second"] = round(len(texts) / elapsed, 1)

    return predictions, raw_scores, config_info


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, Any]:
    """Compute per-SDG and aggregate multi-label classification metrics.

    Args:
        y_true: (N, 17) binary ground truth
        y_pred: (N, 17) binary predictions
    """
    per_sdg = {}
    total_tp, total_fp, total_fn, total_tn = 0, 0, 0, 0

    for sdg_num in range(1, 18):
        idx = sdg_num - 1
        y_t = y_true[:, idx]
        y_p = y_pred[:, idx]

        tp = int((y_t & y_p).sum())
        fp = int(((~y_t.astype(bool)) & y_p.astype(bool)).sum())
        fn = int((y_t & (~y_p.astype(bool))).sum())
        tn = int(((~y_t.astype(bool)) & (~y_p.astype(bool))).sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_sdg[str(sdg_num)] = {
            "name": SDG_NAMES[sdg_num],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": int(y_t.sum()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn

    # Macro average
    macro_precision = np.mean([v["precision"] for v in per_sdg.values()])
    macro_recall = np.mean([v["recall"] for v in per_sdg.values()])
    macro_f1 = np.mean([v["f1"] for v in per_sdg.values()])

    # Micro average
    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (2 * micro_precision * micro_recall / (micro_precision + micro_recall)
                if (micro_precision + micro_recall) > 0 else 0.0)

    # Subset accuracy (exact match)
    subset_accuracy = int((y_true == y_pred).all(axis=1).sum()) / len(y_true)

    return {
        "per_sdg_metrics": per_sdg,
        "macro_avg": {
            "precision": round(macro_precision, 4),
            "recall": round(macro_recall, 4),
            "f1": round(macro_f1, 4),
        },
        "micro_avg": {
            "precision": round(micro_precision, 4),
            "recall": round(micro_recall, 4),
            "f1": round(micro_f1, 4),
        },
        "subset_accuracy": round(subset_accuracy, 4),
    }


def analyze_false_negatives_with_targets(
    engine: AlignmentEngine,
    texts: List[str],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    raw_scores: np.ndarray,
    max_samples: int = 200,
) -> Dict[str, Any]:
    """Analyze false negatives using target-level alignment.

    For each SDG where the engine missed (false negative), check whether
    the target-level score within that SDG is higher than the goal-level score.
    This reveals whether the target-level signal is stronger and potentially
    more discriminating than the goal-level similarity.

    Args:
        engine: AlignmentEngine instance
        texts: Activity description texts
        y_true: (N, 17) binary ground truth
        y_pred: (N, 17) binary predictions
        raw_scores: (N, 17) goal-level alignment scores
        max_samples: Max FN samples per SDG (to bound runtime)

    Returns:
        Dictionary with per-SDG target-level FN analysis
    """
    from src.config.threshold_config import get_threshold

    per_sdg = {}

    for sdg_num in range(1, 18):
        idx = sdg_num - 1
        # False negatives: ground truth = 1, prediction = 0
        fn_mask = (y_true[:, idx] == 1) & (y_pred[:, idx] == 0)
        fn_indices = np.where(fn_mask)[0]

        if len(fn_indices) == 0:
            per_sdg[str(sdg_num)] = {
                "name": SDG_NAMES[sdg_num],
                "false_negatives": 0,
                "analyzed": 0,
                "above_threshold_rate": None,
                "mean_top_target_score": None,
                "mean_goal_score": None,
            }
            continue

        # Sample if too many
        sample_indices = fn_indices
        if len(fn_indices) > max_samples:
            sample_indices = np.random.RandomState(42).choice(
                fn_indices, max_samples, replace=False
            )

        # Get target IDs for this SDG
        sdg_targets = {tid: t for tid, t in SDG_TARGET_DEFINITIONS.items()
                       if t["sdg_num"] == sdg_num}

        if not sdg_targets:
            per_sdg[str(sdg_num)] = {
                "name": SDG_NAMES[sdg_num],
                "false_negatives": int(fn_mask.sum()),
                "analyzed": len(sample_indices),
                "above_threshold_rate": None,
                "mean_top_target_score": None,
                "mean_goal_score": None,
                "note": "No targets defined for this SDG",
            }
            continue

        # Get goal-level threshold for this SDG
        goal_threshold = get_threshold("st", sdg_num)

        # Compute target scores for each FN
        above_threshold_count = 0
        top_target_scores = []
        goal_scores_for_fn = []

        for i in sample_indices:
            target_scores = engine.align_targets(texts[i], sdg_num=sdg_num)
            if target_scores:
                top_score = max(t["score"] for t in target_scores.values())
                top_target_scores.append(top_score)
                goal_scores_for_fn.append(float(raw_scores[i, idx]))

                # "Above threshold" if the top target score exceeds the
                # goal-level threshold — meaning the target signal was present
                # but got diluted at the goal level
                if top_score >= goal_threshold:
                    above_threshold_count += 1

        n_analyzed = len(sample_indices)
        per_sdg[str(sdg_num)] = {
            "name": SDG_NAMES[sdg_num],
            "false_negatives": int(fn_mask.sum()),
            "analyzed": n_analyzed,
            "goal_threshold": goal_threshold,
            "above_threshold_rate": round(above_threshold_count / n_analyzed, 4) if n_analyzed > 0 else None,
            "mean_top_target_score": round(float(np.mean(top_target_scores)), 4) if top_target_scores else None,
            "mean_goal_score": round(float(np.mean(goal_scores_for_fn)), 4) if goal_scores_for_fn else None,
        }

    # Aggregate
    above_rates = [v["above_threshold_rate"] for v in per_sdg.values() if v["above_threshold_rate"] is not None]
    mean_target_scores = [v["mean_top_target_score"] for v in per_sdg.values() if v["mean_top_target_score"] is not None]
    mean_goal_scores = [v["mean_goal_score"] for v in per_sdg.values() if v["mean_goal_score"] is not None]

    return {
        "per_sdg": per_sdg,
        "overall_above_threshold_rate": round(float(np.mean(above_rates)), 4) if above_rates else None,
        "overall_mean_top_target_score": round(float(np.mean(mean_target_scores)), 4) if mean_target_scores else None,
        "overall_mean_goal_score": round(float(np.mean(mean_goal_scores)), 4) if mean_goal_scores else None,
        "description": (
            "For each false negative (missed SDG), align_targets() computes "
            "target-level similarity. above_threshold_rate = fraction of FNs where "
            "the top target score exceeded the goal-level ST threshold. A high rate "
            "means the target-level signal exists but was diluted when averaged into "
            "the goal-level embedding."
        ),
    }


def generate_report(
    worksheet_name: str,
    engine_mode: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    raw_scores: np.ndarray,
    df: pd.DataFrame,
    config_info: Dict[str, Any],
    full_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Build the full benchmark report dict."""
    metrics = compute_metrics(y_true, y_pred)

    # Ground truth and prediction label stats
    gt_stats = compute_label_stats(y_true)
    pred_stats = compute_label_stats(y_pred)

    # Full dataset vs sample SDG distribution
    full_dist = compute_sdg_distribution(full_df)
    sample_dist = compute_sdg_distribution(df)

    # Description word count stats
    word_counts = df["_word_count"]

    known_limitations = []
    if engine_mode == "hybrid":
        known_limitations.append(
            "sdgBERT does not predict SDG 17; hybrid mode falls back to ST-only for SDG 17"
        )

    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "worksheet": worksheet_name,
            "engine_mode": engine_mode,
            "max_samples": len(df),
            "total_dataset_size": len(full_df),
            "description_word_count": {
                "mean": round(float(word_counts.mean()), 1),
                "median": round(float(word_counts.median()), 1),
                "max": int(word_counts.max()),
                "min": int(word_counts.min()),
            },
            "domain_shift_notes": [
                "AidData descriptions are international development finance text",
                "Model was fine-tuned on Australian local government reports",
                "Descriptions are significantly longer than typical council activity text",
            ],
            "known_limitations": known_limitations,
        },
        "config": config_info,
        "label_statistics": {
            "ground_truth": gt_stats,
            "predicted": pred_stats,
        },
        "sdg_distribution": {
            "full_dataset": full_dist,
            "sample": sample_dist,
        },
        "per_sdg_metrics": metrics["per_sdg_metrics"],
        "aggregate_metrics": {
            "macro_avg": metrics["macro_avg"],
            "micro_avg": metrics["micro_avg"],
            "subset_accuracy": metrics["subset_accuracy"],
        },
    }

    return report


def save_report(
    report: Dict[str, Any],
    worksheet_name: str,
    engine_mode: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    raw_scores: np.ndarray,
    df: pd.DataFrame,
    output_dir: Path,
):
    """Save report to JSON, per-SDG CSV, and per-row predictions CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_ws = worksheet_name.replace(" ", "_").replace(".", "")

    # JSON report
    json_path = output_dir / f"aiddata_benchmark_{safe_ws}_{engine_mode}_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Saved report: {json_path}")

    # Per-SDG metrics CSV
    csv_path = output_dir / f"aiddata_per_sdg_{safe_ws}_{engine_mode}_{timestamp}.csv"
    rows = []
    for sdg_num in range(1, 18):
        m = report["per_sdg_metrics"][str(sdg_num)]
        rows.append({
            "SDG": sdg_num,
            "Name": m["name"],
            "Precision": m["precision"],
            "Recall": m["recall"],
            "F1": m["f1"],
            "Support": m["support"],
            "TP": m["tp"],
            "FP": m["fp"],
            "FN": m["fn"],
            "TN": m["tn"],
        })
    # Add aggregates
    rows.append({"SDG": "macro_avg", "Name": "Macro Average",
                 "Precision": report["aggregate_metrics"]["macro_avg"]["precision"],
                 "Recall": report["aggregate_metrics"]["macro_avg"]["recall"],
                 "F1": report["aggregate_metrics"]["macro_avg"]["f1"]})
    rows.append({"SDG": "micro_avg", "Name": "Micro Average",
                 "Precision": report["aggregate_metrics"]["micro_avg"]["precision"],
                 "Recall": report["aggregate_metrics"]["micro_avg"]["recall"],
                 "F1": report["aggregate_metrics"]["micro_avg"]["f1"]})
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"  Saved per-SDG metrics: {csv_path}")

    # Per-row predictions CSV
    pred_path = output_dir / f"aiddata_predictions_{safe_ws}_{engine_mode}_{timestamp}.csv"
    pred_df = df[["ID", "Description"]].copy() if "ID" in df.columns else pd.DataFrame({"Description": df["Description"]})
    for i in range(1, 18):
        col = f"SDG{i}"
        pred_df[f"gt_{col}"] = y_true[:, i - 1]
        pred_df[f"pred_{col}"] = y_pred[:, i - 1]
        pred_df[f"score_{col}"] = raw_scores[:, i - 1]
    pred_df.to_csv(pred_path, index=False)
    print(f"  Saved predictions: {pred_path}")


def print_summary(report: Dict[str, Any]):
    """Print a concise summary to stdout."""
    meta = report["metadata"]
    agg = report["aggregate_metrics"]
    gt_stats = report["label_statistics"]["ground_truth"]
    pred_stats = report["label_statistics"]["predicted"]

    print(f"\n{'='*70}")
    print(f"BENCHMARK SUMMARY: {meta['worksheet']} / {meta['engine_mode']}")
    print(f"{'='*70}")
    print(f"  Samples: {meta['max_samples']} / {meta['total_dataset_size']} total")
    print(f"  Description words: mean={meta['description_word_count']['mean']}, "
          f"median={meta['description_word_count']['median']}, "
          f"max={meta['description_word_count']['max']}")
    print(f"  Label cardinality: GT={gt_stats['cardinality']}, Pred={pred_stats['cardinality']}")
    print(f"  Runtime: {report['config'].get('runtime_seconds', 'N/A')}s")
    print()
    print(f"  {'Macro Avg':<20} P={agg['macro_avg']['precision']:.3f}  "
          f"R={agg['macro_avg']['recall']:.3f}  F1={agg['macro_avg']['f1']:.3f}")
    print(f"  {'Micro Avg':<20} P={agg['micro_avg']['precision']:.3f}  "
          f"R={agg['micro_avg']['recall']:.3f}  F1={agg['micro_avg']['f1']:.3f}")
    print(f"  {'Subset Accuracy':<20} {agg['subset_accuracy']:.3f}")
    print()
    print(f"  Per-SDG F1 scores:")
    for sdg_num in range(1, 18):
        m = report["per_sdg_metrics"][str(sdg_num)]
        marker = " *" if sdg_num == 17 and meta["engine_mode"] == "hybrid" else ""
        print(f"    SDG {sdg_num:2d} ({m['name']:<30s}): F1={m['f1']:.3f}  "
              f"P={m['precision']:.3f}  R={m['recall']:.3f}  (n={m['support']}){marker}")
    if meta["engine_mode"] == "hybrid":
        print(f"  * SDG 17: sdgBERT does not cover SDG 17; hybrid falls back to ST-only")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark SDG Alignment Engines against AidData dataset"
    )
    parser.add_argument(
        "--max-samples", type=int, default=1000,
        help="Maximum number of rows to sample (default: 1000, use 0 for all rows)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="results/benchmark_aiddata",
        help="Output directory for reports (default: results/benchmark_aiddata)"
    )
    parser.add_argument(
        "--xlsx-path", type=str, default=None,
        help=f"Path to Excel file (default: {XLSX_PATH})"
    )
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx_path) if args.xlsx_path else XLSX_PATH
    output_dir = Path(args.output_dir)
    max_samples = args.max_samples if args.max_samples > 0 else None

    if not xlsx_path.exists():
        print(f"ERROR: Excel file not found: {xlsx_path}")
        sys.exit(1)

    worksheets = ["Centralized ver.", "Extended ver."]
    engine_modes = ["st", "hybrid", "st_target_boost"]

    for ws_name in worksheets:
        print(f"\n{'#'*70}")
        print(f"# WORKSHEET: {ws_name}")
        print(f"{'#'*70}")

        # Load full dataset for distribution comparison
        full_df = pd.read_excel(xlsx_path, sheet_name=ws_name)
        full_df = full_df.dropna(subset=["Description"])
        full_df = full_df[full_df["Description"].str.strip() != ""]
        for col in SDG_COLS:
            full_df[col] = full_df[col].fillna(0).astype(int)

        # Load with sampling
        df = load_aiddata(xlsx_path, ws_name, max_samples)
        texts = df["Description"].tolist()

        # Ground truth matrix
        y_true = df[SDG_COLS].values.astype(int)

        for mode in engine_modes:
            print(f"\n--- {ws_name} / {mode.upper()} ---")
            y_pred, raw_scores, config_info = run_engine(mode, texts, df)

            report = generate_report(
                worksheet_name=ws_name,
                engine_mode=mode,
                y_true=y_true,
                y_pred=y_pred,
                raw_scores=raw_scores,
                df=df,
                config_info=config_info,
                full_df=full_df,
            )

            # Target-level false negative analysis (only for baseline modes)
            if "target_boost" not in mode:
                print("  Running target-level FN analysis...")
                st_engine = AlignmentEngine()
                fn_analysis = analyze_false_negatives_with_targets(
                    st_engine, texts, y_true, y_pred, raw_scores
                )
                report["target_fn_analysis"] = fn_analysis

            save_report(report, ws_name, mode, y_true, y_pred, raw_scores, df, output_dir)
            print_summary(report)

            # Print target FN summary (only for baseline modes)
            if "target_boost" not in mode:
                print("  Target-level FN analysis:")
                for sdg_num in range(1, 18):
                    fn = fn_analysis["per_sdg"][str(sdg_num)]
                    if fn["false_negatives"] == 0:
                        continue
                    above = fn.get("above_threshold_rate", "N/A")
                    top = fn.get("mean_top_target_score", "N/A")
                    goal = fn.get("mean_goal_score", "N/A")
                    above_str = f"{above:.1%}" if isinstance(above, float) else above
                    top_str = f"{top:.3f}" if isinstance(top, float) else top
                    goal_str = f"{goal:.3f}" if isinstance(goal, float) else goal
                    print(f"    SDG {sdg_num:2d}: FN={fn['false_negatives']:4d}  "
                          f"above_thresh={above_str}  target={top_str}  goal={goal_str}")
                overall_above = fn_analysis["overall_above_threshold_rate"]
                overall_top = fn_analysis["overall_mean_top_target_score"]
                overall_goal = fn_analysis["overall_mean_goal_score"]
                above_str = f"{overall_above:.1%}" if isinstance(overall_above, float) else "N/A"
                top_str = f"{overall_top:.3f}" if isinstance(overall_top, float) else "N/A"
                goal_str = f"{overall_goal:.3f}" if isinstance(overall_goal, float) else "N/A"
                print(f"    Overall: above_thresh={above_str}  target={top_str}  goal={goal_str}")
                print()

    print("\nBenchmark complete.")


if __name__ == "__main__":
    main()