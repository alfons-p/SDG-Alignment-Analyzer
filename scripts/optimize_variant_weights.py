#!/usr/bin/env python3
"""Optimize variant embedding weights using coarse-to-fine grid search with 5-fold CV.

Uses the same 20%/60%/20% data split as finetune_with_variants.py (same random seed).
The 20% weight optimization set has NO overlap with the 60% fine-tuning set.

Pre-computes per-variant similarity matrices once, then evaluates weight combinations
by computing weighted combinations — avoiding redundant embedding computation.

Grid search:
  - Coarse: 5D simplex at 0.20 intervals (~126 combinations)
  - Fine: 0.05 intervals around top regions (~200-300 evaluations)
  - Primary metric: AidData Macro F1
  - Secondary constraint: OSDG accuracy >= 87.6% baseline

Output: optimal weights, per-fold results, and out-of-sample evaluation.
"""

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

import sys
sys_path = Path(__file__).parent.parent
sys.path.insert(0, str(sys_path))

from src.config.sdg_definitions import SDG_DEFINITIONS
from src.config.sdg_target_definitions import SDG_TARGET_DEFINITIONS, get_targets_for_sdg
from src.config.threshold_config import get_threshold

SDG_COLS = [f"SDG{i}" for i in range(1, 18)]
VARIANT_NAMES = ['core', 'local_gov', 'targets', 'keywords', 'indicators']
OSDG_ACCURACY_BASELINE = 0.876


# --- SDG text variant generation (matches sdg_reference.py) ---

def build_sdg_variant_texts(sdg_num: int) -> Dict[str, str]:
    """Build all variant texts for an SDG (matching sdg_reference.py exactly)."""
    sdg = SDG_DEFINITIONS.get(sdg_num, {})
    variants = {}

    # Core
    variants['core'] = f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('description', '')}"

    # Local government
    local_gov_keywords = sdg.get('local_gov_keywords', [])
    if local_gov_keywords:
        variants['local_gov'] = (
            f"Local government and council activities for {sdg.get('name', '')}: "
            + ", ".join(local_gov_keywords[:30])
        )
    else:
        variants['local_gov'] = variants['core']

    # Indicators
    indicators = sdg.get('indicators', [])
    targets_list = sdg.get('targets', [])
    if indicators:
        variants['indicators'] = (
            f"UN Sustainable Development Goals targets and indicators for {sdg.get('name', '')}: "
            + ", ".join(indicators[:5])
        )
    elif targets_list:
        variants['indicators'] = f"SDG {sdg_num} targets: " + ", ".join(targets_list)
    else:
        variants['indicators'] = variants['core']

    # Keywords
    all_keywords = []
    all_keywords.extend(sdg.get('keywords', []))
    all_keywords.extend(sdg.get('local_gov_keywords', [])[:20])
    if all_keywords:
        variants['keywords'] = (
            f"Keywords for SDG {sdg_num} {sdg.get('name', '')}: "
            + ", ".join(all_keywords[:40])
        )
    else:
        variants['keywords'] = variants['core']

    # Targets variant: per-target texts (will be encoded individually then averaged)
    target_texts = _build_target_texts(sdg_num)
    variants['targets'] = target_texts  # This is a list, not a single string

    return variants


def _build_target_texts(sdg_num: int) -> List[str]:
    """Build per-target texts for the targets variant."""
    targets = get_targets_for_sdg(sdg_num)
    if not targets:
        sdg = SDG_DEFINITIONS.get(sdg_num, {})
        return [f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('short_description', '')}"]

    texts = []
    for target_id, target_def in targets.items():
        texts.append(
            f"Target {target_id} of SDG {sdg_num}: "
            f"{target_def['target_text']}. "
            f"In plain terms: {target_def['layman_description']}"
        )
    return texts


# --- Data loading (matches finetune_with_variants.py) ---

def load_osdg_data(csv_path: Path, min_agreement: float = 0.7) -> pd.DataFrame:
    """Load OSDG Community Dataset with quality filtering."""
    print(f"Loading OSDG data from {csv_path}...")
    try:
        df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')
    except TypeError:
        df = pd.read_csv(csv_path, sep='\t', error_bad_lines=False)

    print(f"Total OSDG records: {len(df)}")
    df = df[df['agreement'] >= min_agreement].copy()
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]
    df = df[df['sdg'].isin(range(1, 18))]
    print(f"OSDG records after filtering (agreement >= {min_agreement}): {len(df)}")
    return df


def load_aiddata_data(xlsx_path: Path) -> pd.DataFrame:
    """Load AidData Chinese Development Finance dataset."""
    print(f"Loading AidData from {xlsx_path}...")
    df = pd.read_excel(xlsx_path, sheet_name="Extended ver.")
    df = df.dropna(subset=["Description"])
    df = df[df["Description"].str.strip() != ""]
    df = df.dropna(subset=SDG_COLS, how="all")
    for col in SDG_COLS:
        df[col] = df[col].fillna(0).astype(int)
    print(f"AidData records: {len(df)}")
    return df


# --- Stratified splitting (matches finetune_with_variants.py) ---

def stratified_split_by_sdg(df, sdg_labels, test_frac=0.2, random_state=42):
    """Split dataframe stratified by SDG (same as finetune_with_variants.py)."""
    rng = np.random.RandomState(random_state)
    train_indices, test_indices = [], []

    for sdg_num in range(1, 18):
        mask = sdg_labels == sdg_num
        indices = np.where(mask)[0]
        rng.shuffle(indices)
        n_test = max(1, int(len(indices) * test_frac))
        test_indices.extend(indices[:n_test])
        train_indices.extend(indices[n_test:])

    return df.iloc[train_indices].reset_index(drop=True), df.iloc[test_indices].reset_index(drop=True)


# --- Pre-computation of per-variant similarity matrices ---

def precompute_variant_embeddings(model: SentenceTransformer) -> Dict[str, Dict[int, np.ndarray]]:
    """Pre-compute SDG embeddings for each variant separately.

    Returns dict mapping variant_name -> {sdg_num: embedding}.
    For 'targets' variant, each target is encoded individually then averaged.
    """
    print("\nPre-computing per-variant SDG embeddings...")
    variant_embeddings = {v: {} for v in VARIANT_NAMES}

    for sdg_num in range(1, 18):
        sdg = SDG_DEFINITIONS.get(sdg_num, {})

        # Core
        core_text = f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('description', '')}"
        variant_embeddings['core'][sdg_num] = model.encode(core_text, convert_to_numpy=True)

        # Local government
        local_gov_keywords = sdg.get('local_gov_keywords', [])
        if local_gov_keywords:
            local_text = (f"Local government and council activities for {sdg.get('name', '')}: "
                          + ", ".join(local_gov_keywords[:30]))
        else:
            local_text = core_text
        variant_embeddings['local_gov'][sdg_num] = model.encode(local_text, convert_to_numpy=True)

        # Targets (per-target encoding + averaging, matching sdg_reference.py)
        targets = get_targets_for_sdg(sdg_num)
        if targets:
            target_texts = []
            for target_id, target_def in targets.items():
                target_texts.append(
                    f"Target {target_id} of SDG {sdg_num}: "
                    f"{target_def['target_text']}. "
                    f"In plain terms: {target_def['layman_description']}"
                )
            target_embs = model.encode(target_texts, convert_to_numpy=True)
            avg_emb = np.mean(target_embs, axis=0)
            norm = np.linalg.norm(avg_emb)
            if norm > 0:
                avg_emb = avg_emb / norm
            variant_embeddings['targets'][sdg_num] = avg_emb
        else:
            fallback = f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('short_description', '')}"
            variant_embeddings['targets'][sdg_num] = model.encode(fallback, convert_to_numpy=True)

        # Keywords
        all_keywords = list(sdg.get('keywords', []))
        all_keywords.extend(sdg.get('local_gov_keywords', [])[:20])
        if all_keywords:
            kw_text = f"Keywords for SDG {sdg_num} {sdg.get('name', '')}: " + ", ".join(all_keywords[:40])
        else:
            kw_text = core_text
        variant_embeddings['keywords'][sdg_num] = model.encode(kw_text, convert_to_numpy=True)

        # Indicators
        indicators = sdg.get('indicators', [])
        targets_list = sdg.get('targets', [])
        if indicators:
            ind_text = (f"UN Sustainable Development Goals targets and indicators for {sdg.get('name', '')}: "
                        + ", ".join(indicators[:5]))
        elif targets_list:
            ind_text = f"SDG {sdg_num} targets: " + ", ".join(targets_list)
        else:
            ind_text = core_text
        variant_embeddings['indicators'][sdg_num] = model.encode(ind_text, convert_to_numpy=True)

    print(f"  Computed embeddings for {len(VARIANT_NAMES)} variants × 17 SDGs")
    return variant_embeddings


def precompute_activity_embeddings(model: SentenceTransformer, texts: List[str],
                                   batch_size: int = 64) -> np.ndarray:
    """Encode all activity texts using the model."""
    print(f"\nEncoding {len(texts)} activity texts...")
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True,
                               convert_to_numpy=True)
    return embeddings


def compute_variant_similarity_matrices(
    variant_embeddings: Dict[str, Dict[int, np.ndarray]],
    activity_embeddings: np.ndarray,
) -> Dict[str, np.ndarray]:
    """Compute cosine similarity matrices for each variant.

    Returns dict mapping variant_name -> (N_activities, 17) similarity matrix.
    """
    print("Computing per-variant cosine similarity matrices...")
    sim_matrices = {}

    for variant_name in VARIANT_NAMES:
        # Stack SDG embeddings into (17, dim) matrix
        sdg_embs = np.vstack([variant_embeddings[variant_name][i] for i in range(1, 18)])
        # L2-normalize SDG embeddings
        norms = np.linalg.norm(sdg_embs, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        sdg_embs_norm = sdg_embs / norms

        # L2-normalize activity embeddings
        act_norms = np.linalg.norm(activity_embeddings, axis=1, keepdims=True)
        act_norms = np.where(act_norms > 0, act_norms, 1.0)
        act_embs_norm = activity_embeddings / act_norms

        # Cosine similarity: (N, dim) @ (dim, 17) -> (N, 17)
        sim = act_embs_norm @ sdg_embs_norm.T
        sim_matrices[variant_name] = sim

    print(f"  Computed {len(sim_matrices)} similarity matrices of shape {sim_matrices[VARIANT_NAMES[0]].shape}")
    return sim_matrices


def combine_similarity_matrices(
    sim_matrices: Dict[str, np.ndarray],
    weights: Dict[str, float],
) -> np.ndarray:
    """Combine per-variant similarity matrices using weighted sum.

    Args:
        sim_matrices: Dict mapping variant_name -> (N, 17) similarity matrix
        weights: Dict mapping variant_name -> weight (must sum to 1)

    Returns:
        (N, 17) combined similarity matrix
    """
    total_weight = sum(weights.values())
    if total_weight <= 0:
        total_weight = 1.0

    combined = np.zeros_like(sim_matrices[VARIANT_NAMES[0]])
    for variant_name, sim in sim_matrices.items():
        w = weights.get(variant_name, 0.0) / total_weight
        combined += w * sim

    return combined


# --- Evaluation metrics ---

def evaluate_weights_on_aiddata(
    combined_scores: np.ndarray,
    y_true: np.ndarray,
    thresholds: Dict[int, float],
) -> Dict[str, float]:
    """Evaluate weight combination on AidData multi-label classification.

    Args:
        combined_scores: (N, 17) combined similarity scores
        y_true: (N, 17) binary ground truth
        thresholds: per-SDG thresholds

    Returns:
        Dict with macro_f1, macro_precision, macro_recall
    """
    predictions = np.zeros_like(combined_scores, dtype=int)
    for sdg_num in range(1, 18):
        idx = sdg_num - 1
        predictions[:, idx] = (combined_scores[:, idx] >= thresholds[sdg_num]).astype(int)

    per_sdg_f1 = []
    per_sdg_precision = []
    per_sdg_recall = []

    for sdg_num in range(1, 18):
        idx = sdg_num - 1
        y_t = y_true[:, idx]
        y_p = predictions[:, idx]

        tp = int((y_t & y_p).sum())
        fp = int(((~y_t.astype(bool)) & y_p.astype(bool)).sum())
        fn = int((y_t & (~y_p.astype(bool))).sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_sdg_f1.append(f1)
        per_sdg_precision.append(precision)
        per_sdg_recall.append(recall)

    return {
        'macro_f1': float(np.mean(per_sdg_f1)),
        'macro_precision': float(np.mean(per_sdg_precision)),
        'macro_recall': float(np.mean(per_sdg_recall)),
    }


def evaluate_weights_on_osdg(
    combined_scores: np.ndarray,
    osdg_labels: np.ndarray,
    thresholds: Dict[int, float],
) -> Dict[str, float]:
    """Evaluate weight combination on OSDG single-label top-1 accuracy.

    Args:
        combined_scores: (N, 17) combined similarity scores
        osdg_labels: (N,) array of true SDG labels
        thresholds: per-SDG thresholds

    Returns:
        Dict with accuracy (top-1 prediction matches label)
    """
    pred_sdg = np.argmax(combined_scores, axis=1) + 1  # SDG 1-17
    correct = (pred_sdg == osdg_labels).sum()
    accuracy = correct / len(osdg_labels) if len(osdg_labels) > 0 else 0.0
    return {'accuracy': float(accuracy)}


# --- Grid generation ---

def generate_simplex_grid(dim: int, step: float) -> List[List[float]]:
    """Generate points on the (dim-1)-simplex with given step size.

    All points satisfy: sum(x_i) = 1.0, x_i >= 0.
    Uses integer enumeration: k_i >= 0, sum(k_i) = round(1/step).
    """
    n_units = round(1.0 / step)
    grid = []

    def _enumerate(remaining_units, remaining_dims, current):
        if remaining_dims == 1:
            grid.append(current + [remaining_units * step])
            return
        for k in range(remaining_units + 1):
            _enumerate(remaining_units - k, remaining_dims - 1, current + [k * step])

    _enumerate(n_units, dim, [])
    return grid


# --- 5-fold stratified CV ---

def create_5fold_splits(df, sdg_labels, n_folds=5, random_state=100):
    """Create 5-fold stratified splits from a DataFrame.

    Returns list of (train_indices, val_indices) tuples.
    """
    rng = np.random.RandomState(random_state)
    indices_by_sdg = defaultdict(list)

    for idx, sdg_num in enumerate(sdg_labels):
        indices_by_sdg[int(sdg_num)].append(idx)

    # Shuffle within each SDG group
    for sdg_num in indices_by_sdg:
        rng.shuffle(indices_by_sdg[sdg_num])

    # Assign each index to a fold
    fold_assignment = np.zeros(len(df), dtype=int)
    for sdg_num, indices in indices_by_sdg.items():
        for i, idx in enumerate(indices):
            fold_assignment[idx] = i % n_folds

    folds = []
    for fold_id in range(n_folds):
        val_mask = fold_assignment == fold_id
        train_mask = ~val_mask
        val_indices = np.where(val_mask)[0]
        train_indices = np.where(train_mask)[0]
        folds.append((train_indices, val_indices))

    return folds


# --- Main optimization ---

def main():
    parser = argparse.ArgumentParser(
        description="Optimize variant embedding weights with coarse-to-fine grid search"
    )
    parser.add_argument("--model", default="models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509",
                        help="Fine-tuned model path (should be the re-fine-tuned variant model)")
    parser.add_argument("--device", default=None,
                        help="Device for model (default: auto-detect). Use 'cpu' to avoid GPU contention.")
    parser.add_argument("--osdg-path", default="data/external/osdg-community-data-v2024-04-01.csv",
                        help="Path to OSDG Community Dataset")
    parser.add_argument("--aiddata-path",
                        default="data/external/30015124/Chinese_Development_Finance_SDG_Categorizations_2000-2021.xlsx",
                        help="Path to AidData Excel file")
    parser.add_argument("--min-agreement", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-aiddata", action="store_true",
                        help="Skip AidData (OSDG only)")
    parser.add_argument("--coarse-step", type=float, default=0.20,
                        help="Coarse grid step size (default: 0.20)")
    parser.add_argument("--fine-step", type=float, default=0.05,
                        help="Fine grid step size (default: 0.05)")
    parser.add_argument("--top-k-regions", type=int, default=5,
                        help="Number of top coarse regions to refine (default: 5)")
    parser.add_argument("--output-dir", default="results/weight_optimization",
                        help="Output directory for results")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Load data and replicate the 20/60/20 split (same seed as finetune script) ---

    osdg_df = load_osdg_data(Path(args.osdg_path), args.min_agreement)
    aiddata_df = None if args.skip_aiddata else load_aiddata_data(Path(args.aiddata_path))

    # OSDG splits (same as finetune_with_variants.py)
    osdg_outofsample, osdg_remaining = stratified_split_by_sdg(
        osdg_df, osdg_df['sdg'].astype(int), test_frac=0.2, random_state=args.seed
    )
    osdg_finetune, osdg_weightopt = stratified_split_by_sdg(
        osdg_remaining, osdg_remaining['sdg'].astype(int), test_frac=0.25, random_state=args.seed + 1
    )

    print(f"\nOSDG splits: out-of-sample={len(osdg_outofsample)}, "
          f"fine-tuning={len(osdg_finetune)}, weight-optimization={len(osdg_weightopt)}")

    # AidData splits (same as finetune_with_variants.py)
    aiddata_outofsample = aiddata_finetune = aiddata_weightopt = None
    if aiddata_df is not None:
        aiddata_primary_sdg = aiddata_df[SDG_COLS].values.argmax(axis=1) + 1
        aiddata_outofsample, aiddata_remaining = stratified_split_by_sdg(
            aiddata_df, pd.Series(aiddata_primary_sdg), test_frac=0.2, random_state=args.seed
        )
        aiddata_finetune, aiddata_weightopt = stratified_split_by_sdg(
            aiddata_remaining,
            pd.Series(aiddata_remaining[SDG_COLS].values.argmax(axis=1) + 1),
            test_frac=0.25, random_state=args.seed + 1
        )
        print(f"AidData splits: out-of-sample={len(aiddata_outofsample)}, "
              f"fine-tuning={len(aiddata_finetune)}, weight-optimization={len(aiddata_weightopt)}")

    # Verify no overlap between fine-tuning and weight optimization
    osdg_overlap = set(osdg_finetune.index) & set(osdg_weightopt.index)
    print(f"OSDG overlap check (should be 0): {len(osdg_overlap)}")

    # --- Load model ---

    print(f"\nLoading model: {args.model}")
    model_kwargs = {}
    if args.device:
        model_kwargs['device'] = args.device
    model = SentenceTransformer(args.model, **model_kwargs)

    # --- Pre-compute variant embeddings ---

    variant_embeddings = precompute_variant_embeddings(model)

    # --- Pre-compute activity embeddings and similarity matrices for all splits ---

    thresholds = {sdg_num: get_threshold("st", sdg_num) for sdg_num in range(1, 18)}

    # OSDG weight optimization set
    print("\n--- OSDG weight optimization set ---")
    osdg_weightopt_texts = osdg_weightopt['text'].tolist()
    osdg_weightopt_labels = osdg_weightopt['sdg'].astype(int).values
    osdg_weightopt_embs = precompute_activity_embeddings(model, osdg_weightopt_texts)
    osdg_weightopt_sims = compute_variant_similarity_matrices(variant_embeddings, osdg_weightopt_embs)

    # OSDG out-of-sample set
    print("\n--- OSDG out-of-sample set ---")
    osdg_oos_texts = osdg_outofsample['text'].tolist()
    osdg_oos_labels = osdg_outofsample['sdg'].astype(int).values
    osdg_oos_embs = precompute_activity_embeddings(model, osdg_oos_texts)
    osdg_oos_sims = compute_variant_similarity_matrices(variant_embeddings, osdg_oos_embs)

    # AidData weight optimization set
    aiddata_weightopt_sims = None
    aiddata_weightopt_y = None
    aiddata_oos_sims = None
    aiddata_oos_y = None

    if aiddata_weightopt is not None:
        print("\n--- AidData weight optimization set ---")
        aiddata_weightopt_texts = aiddata_weightopt['Description'].tolist()
        aiddata_weightopt_y = aiddata_weightopt[SDG_COLS].values.astype(int)
        aiddata_weightopt_embs = precompute_activity_embeddings(model, aiddata_weightopt_texts)
        aiddata_weightopt_sims = compute_variant_similarity_matrices(variant_embeddings, aiddata_weightopt_embs)

        print("\n--- AidData out-of-sample set ---")
        aiddata_oos_texts = aiddata_outofsample['Description'].tolist()
        aiddata_oos_y = aiddata_outofsample[SDG_COLS].values.astype(int)
        aiddata_oos_embs = precompute_activity_embeddings(model, aiddata_oos_texts)
        aiddata_oos_sims = compute_variant_similarity_matrices(variant_embeddings, aiddata_oos_embs)

    # --- 5-fold CV on weight optimization set ---

    print("\n" + "=" * 70)
    print("5-FOLD CROSS-VALIDATION GRID SEARCH")
    print("=" * 70)

    # Create folds
    osdg_folds = create_5fold_splits(osdg_weightopt, osdg_weightopt_labels, n_folds=5, random_state=100)

    aiddata_folds = None
    if aiddata_weightopt is not None:
        aiddata_primary = aiddata_weightopt[SDG_COLS].values.argmax(axis=1) + 1
        aiddata_folds = create_5fold_splits(aiddata_weightopt, aiddata_primary, n_folds=5, random_state=100)

    # --- Coarse grid search ---

    dim = len(VARIANT_NAMES)
    coarse_grid = generate_simplex_grid(dim, args.coarse_step)
    print(f"\nCoarse grid: {len(coarse_grid)} combinations at step={args.coarse_step}")

    coarse_results = []

    for weights_list in tqdm(coarse_grid, desc="Coarse grid"):
        weights = {name: w for name, w in zip(VARIANT_NAMES, weights_list)}

        # Evaluate on each fold
        fold_scores = []

        for fold_id, (train_idx, val_idx) in enumerate(osdg_folds):
            # OSDG fold
            osdg_val_sims = {v: sim[val_idx] for v, sim in osdg_weightopt_sims.items()}
            combined = combine_similarity_matrices(osdg_val_sims, weights)
            osdg_metrics = evaluate_weights_on_osdg(combined, osdg_weightopt_labels[val_idx], thresholds)

            # AidData fold (if available)
            aiddata_metrics = {'macro_f1': 0.0}
            if aiddata_folds is not None and aiddata_weightopt_sims is not None:
                a_train_idx, a_val_idx = aiddata_folds[fold_id]
                aid_val_sims = {v: sim[a_val_idx] for v, sim in aiddata_weightopt_sims.items()}
                combined_aid = combine_similarity_matrices(aid_val_sims, weights)
                aiddata_metrics = evaluate_weights_on_aiddata(combined_aid, aiddata_weightopt_y[a_val_idx], thresholds)

            fold_scores.append({
                'osdg_accuracy': osdg_metrics['accuracy'],
                'aiddata_macro_f1': aiddata_metrics['macro_f1'],
            })

        # Average across folds
        avg_osdg_acc = np.mean([f['osdg_accuracy'] for f in fold_scores])
        avg_aiddata_f1 = np.mean([f['aiddata_macro_f1'] for f in fold_scores])

        coarse_results.append({
            'weights': weights,
            'avg_osdg_accuracy': avg_osdg_acc,
            'avg_aiddata_macro_f1': avg_aiddata_f1,
            'fold_scores': fold_scores,
            'passes_constraint': avg_osdg_acc >= OSDG_ACCURACY_BASELINE,
        })

    # Sort by primary metric (AidData Macro F1), prefer those passing OSDG constraint
    coarse_results.sort(key=lambda x: (x['passes_constraint'], x['avg_aiddata_macro_f1']), reverse=True)

    print(f"\nTop {args.top_k_regions} coarse grid results:")
    for i, r in enumerate(coarse_results[:args.top_k_regions]):
        w = r['weights']
        constraint = "PASS" if r['passes_constraint'] else "FAIL"
        print(f"  {i+1}. F1={r['avg_aiddata_macro_f1']:.4f}  OSDG_acc={r['avg_osdg_accuracy']:.4f} [{constraint}]  "
              f"w=({w['core']:.2f}, {w['local_gov']:.2f}, {w['targets']:.2f}, {w['keywords']:.2f}, {w['indicators']:.2f})")

    # --- Fine grid search around top regions ---

    top_weights = [r['weights'] for r in coarse_results[:args.top_k_regions]]

    fine_grid_set = set()
    for center in top_weights:
        center_list = [center[v] for v in VARIANT_NAMES]
        # Generate fine grid points around this center
        fine_local = generate_simplex_grid(dim, args.fine_step)
        for pt in fine_local:
            # Only keep points within a neighborhood of the center
            dist = sum(abs(pt[i] - center_list[i]) for i in range(dim))
            if dist <= dim * args.coarse_step:  # Within one coarse step
                fine_grid_set.add(tuple(round(x, 4) for x in pt))

    # Remove points already in coarse grid
    coarse_set = set(tuple(round(x[i], 4) for i in range(dim)) for x in coarse_grid)
    fine_grid_unique = [list(pt) for pt in fine_grid_set if pt not in coarse_set]

    print(f"\nFine grid: {len(fine_grid_unique)} new combinations around top {args.top_k_regions} regions")

    fine_results = []

    for weights_list in tqdm(fine_grid_unique, desc="Fine grid"):
        weights = {name: w for name, w in zip(VARIANT_NAMES, weights_list)}

        fold_scores = []
        for fold_id, (train_idx, val_idx) in enumerate(osdg_folds):
            osdg_val_sims = {v: sim[val_idx] for v, sim in osdg_weightopt_sims.items()}
            combined = combine_similarity_matrices(osdg_val_sims, weights)
            osdg_metrics = evaluate_weights_on_osdg(combined, osdg_weightopt_labels[val_idx], thresholds)

            aiddata_metrics = {'macro_f1': 0.0}
            if aiddata_folds is not None and aiddata_weightopt_sims is not None:
                a_train_idx, a_val_idx = aiddata_folds[fold_id]
                aid_val_sims = {v: sim[a_val_idx] for v, sim in aiddata_weightopt_sims.items()}
                combined_aid = combine_similarity_matrices(aid_val_sims, weights)
                aiddata_metrics = evaluate_weights_on_aiddata(combined_aid, aiddata_weightopt_y[a_val_idx], thresholds)

            fold_scores.append({
                'osdg_accuracy': osdg_metrics['accuracy'],
                'aiddata_macro_f1': aiddata_metrics['macro_f1'],
            })

        avg_osdg_acc = np.mean([f['osdg_accuracy'] for f in fold_scores])
        avg_aiddata_f1 = np.mean([f['aiddata_macro_f1'] for f in fold_scores])

        fine_results.append({
            'weights': weights,
            'avg_osdg_accuracy': avg_osdg_acc,
            'avg_aiddata_macro_f1': avg_aiddata_f1,
            'fold_scores': fold_scores,
            'passes_constraint': avg_osdg_acc >= OSDG_ACCURACY_BASELINE,
        })

    # Combine coarse + fine results and find the best
    all_results = coarse_results + fine_results
    all_results.sort(key=lambda x: (x['passes_constraint'], x['avg_aiddata_macro_f1']), reverse=True)

    best = all_results[0]
    print(f"\n{'=' * 70}")
    print("BEST WEIGHT COMBINATION (5-FOLD CV)")
    print(f"{'=' * 70}")
    w = best['weights']
    constraint = "PASS" if best['passes_constraint'] else "FAIL"
    print(f"  AidData Macro F1: {best['avg_aiddata_macro_f1']:.4f}")
    print(f"  OSDG Accuracy:    {best['avg_osdg_accuracy']:.4f} [{constraint}]")
    print(f"  Weights:")
    for name in VARIANT_NAMES:
        print(f"    {name:12s}: {w[name]:.4f}")

    # --- Per-fold best weights (for averaging) ---
    # Also compute per-fold-optimal weights to average (robustness check)
    per_fold_bests = []
    for fold_id in range(5):
        fold_best = None
        fold_best_f1 = -1
        for r in all_results:
            if r['fold_scores'][fold_id]['aiddata_macro_f1'] > fold_best_f1:
                if r['passes_constraint'] or r['fold_scores'][fold_id]['osdg_accuracy'] >= OSDG_ACCURACY_BASELINE:
                    fold_best_f1 = r['fold_scores'][fold_id]['aiddata_macro_f1']
                    fold_best = r
        if fold_best:
            per_fold_bests.append(fold_best['weights'])

    # Average per-fold best weights
    if per_fold_bests:
        avg_weights = {}
        for name in VARIANT_NAMES:
            avg_weights[name] = float(np.mean([w[name] for w in per_fold_bests]))
        # Normalize to sum to 1
        total = sum(avg_weights.values())
        for name in VARIANT_NAMES:
            avg_weights[name] = round(avg_weights[name] / total, 4)
        print(f"\n  Averaged per-fold-optimal weights:")
        for name in VARIANT_NAMES:
            print(f"    {name:12s}: {avg_weights[name]:.4f}")
    else:
        avg_weights = best['weights']

    # Use the averaged weights as final weights
    final_weights = avg_weights

    # --- Out-of-sample evaluation ---

    print(f"\n{'=' * 70}")
    print("OUT-OF-SAMPLE EVALUATION")
    print(f"{'=' * 70}")

    # OSDG out-of-sample
    osdg_oos_combined = combine_similarity_matrices(osdg_oos_sims, final_weights)
    osdg_oos_metrics = evaluate_weights_on_osdg(osdg_oos_combined, osdg_oos_labels, thresholds)
    print(f"\n  OSDG out-of-sample accuracy: {osdg_oos_metrics['accuracy']:.4f}")

    # AidData out-of-sample
    aiddata_oos_metrics = None
    if aiddata_oos_sims is not None and aiddata_oos_y is not None:
        aiddata_oos_combined = combine_similarity_matrices(aiddata_oos_sims, final_weights)
        aiddata_oos_metrics = evaluate_weights_on_aiddata(aiddata_oos_combined, aiddata_oos_y, thresholds)
        print(f"  AidData out-of-sample Macro F1: {aiddata_oos_metrics['macro_f1']:.4f}")
        print(f"  AidData out-of-sample Macro Precision: {aiddata_oos_metrics['macro_precision']:.4f}")
        print(f"  AidData out-of-sample Macro Recall: {aiddata_oos_metrics['macro_recall']:.4f}")

        # Per-SDG breakdown
        predictions = np.zeros_like(aiddata_oos_combined, dtype=int)
        for sdg_num in range(1, 18):
            idx = sdg_num - 1
            predictions[:, idx] = (aiddata_oos_combined[:, idx] >= thresholds[sdg_num]).astype(int)

        print(f"\n  Per-SDG out-of-sample results:")
        for sdg_num in range(1, 18):
            idx = sdg_num - 1
            y_t = aiddata_oos_y[:, idx]
            y_p = predictions[:, idx]
            tp = int((y_t & y_p).sum())
            fp = int(((~y_t.astype(bool)) & y_p.astype(bool)).sum())
            fn = int((y_t & (~y_p.astype(bool))).sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            name = SDG_DEFINITIONS[sdg_num]['name']
            print(f"    SDG {sdg_num:2d} ({name:<30s}): F1={f1:.3f}  P={prec:.3f}  R={rec:.3f}  (n={int(y_t.sum())})")

        # FP rate
        total_positive = int(predictions.sum())
        total_fp = sum(
            int(((~aiddata_oos_y[:, i].astype(bool)) & predictions[:, i].astype(bool)).sum())
            for i in range(17)
        )
        fp_rate = total_fp / total_positive if total_positive > 0 else 0.0
        print(f"\n  Overall FP rate: {fp_rate:.4f} ({total_fp}/{total_positive})")

    # --- Comparison with old weights ---

    print(f"\n{'=' * 70}")
    print("COMPARISON WITH OLD WEIGHTS")
    print(f"{'=' * 70}")

    old_weights = {'core': 0.35, 'local_gov': 0.30, 'keywords': 0.20, 'indicators': 0.15}
    # Old system didn't have targets variant; compare by setting targets=0

    # For old weights, we need a 4-variant comparison (without targets)
    # But our sim matrices include targets. We'll set targets weight to 0.
    old_weights_with_zero_targets = {'core': 0.35, 'local_gov': 0.30, 'targets': 0.0,
                                      'keywords': 0.20, 'indicators': 0.15}
    # Normalize remaining weights
    non_zero_sum = sum(v for v in old_weights_with_zero_targets.values() if v > 0)
    old_weights_normalized = {k: v / non_zero_sum if v > 0 else 0.0
                               for k, v in old_weights_with_zero_targets.items()}

    # OSDG out-of-sample with old weights
    osdg_oos_old_combined = combine_similarity_matrices(osdg_oos_sims, old_weights_normalized)
    osdg_oos_old_metrics = evaluate_weights_on_osdg(osdg_oos_old_combined, osdg_oos_labels, thresholds)
    print(f"\n  OSDG out-of-sample accuracy (old weights): {osdg_oos_old_metrics['accuracy']:.4f}")
    print(f"  OSDG out-of-sample accuracy (new weights): {osdg_oos_metrics['accuracy']:.4f}")

    if aiddata_oos_sims is not None and aiddata_oos_y is not None:
        aiddata_oos_old_combined = combine_similarity_matrices(aiddata_oos_sims, old_weights_normalized)
        aiddata_oos_old_metrics = evaluate_weights_on_aiddata(aiddata_oos_old_combined, aiddata_oos_y, thresholds)
        print(f"\n  AidData out-of-sample Macro F1 (old weights): {aiddata_oos_old_metrics['macro_f1']:.4f}")
        print(f"  AidData out-of-sample Macro F1 (new weights): {aiddata_oos_metrics['macro_f1']:.4f}")

    # --- Save results ---

    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'model': args.model,
            'seed': args.seed,
            'coarse_step': args.coarse_step,
            'fine_step': args.fine_step,
            'top_k_regions': args.top_k_regions,
            'osdg_accuracy_baseline': OSDG_ACCURACY_BASELINE,
        },
        'final_weights': final_weights,
        'cv_best': {
            'weights': best['weights'],
            'avg_aiddata_macro_f1': best['avg_aiddata_macro_f1'],
            'avg_osdg_accuracy': best['avg_osdg_accuracy'],
            'passes_constraint': best['passes_constraint'],
        },
        'out_of_sample': {
            'osdg_accuracy': osdg_oos_metrics['accuracy'],
            'aiddata_macro_f1': aiddata_oos_metrics['macro_f1'] if aiddata_oos_metrics else None,
            'aiddata_macro_precision': aiddata_oos_metrics['macro_precision'] if aiddata_oos_metrics else None,
            'aiddata_macro_recall': aiddata_oos_metrics['macro_recall'] if aiddata_oos_metrics else None,
        },
        'comparison_old_weights': {
            'old_weights': old_weights_normalized,
            'osdg_accuracy_old': osdg_oos_old_metrics['accuracy'],
            'aiddata_macro_f1_old': aiddata_oos_old_metrics['macro_f1'] if aiddata_oos_metrics else None,
        },
        'coarse_grid_top10': [
            {
                'weights': r['weights'],
                'avg_aiddata_macro_f1': r['avg_aiddata_macro_f1'],
                'avg_osdg_accuracy': r['avg_osdg_accuracy'],
                'passes_constraint': r['passes_constraint'],
            }
            for r in coarse_results[:10]
        ],
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = output_dir / f"weight_optimization_{timestamp}.json"

    # Custom JSON encoder for numpy types
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            elif isinstance(obj, (np.floating,)):
                return float(obj)
            elif isinstance(obj, (np.bool_,)):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)
    print(f"\nResults saved to: {results_path}")

    # Print final weights in copy-pasteable format
    print(f"\n{'=' * 70}")
    print("FINAL OPTIMIZED WEIGHTS (for src/sdg_reference.py)")
    print(f"{'=' * 70}")
    print("default_weights = {")
    for name in VARIANT_NAMES:
        print(f"    '{name}': {final_weights[name]:.4f},")
    print("}")

    print(f"\n{'=' * 70}")
    print("Weight optimization complete!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()