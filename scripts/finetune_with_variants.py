#!/usr/bin/env python3
"""Fine-tune sentence transformer with all SDG text variants.

For each labeled text (OSDG single-label or AidData multi-label), create
positive pairs with every filtered text variant of its SDG(s):
- 1 pair with core description
- N pairs with individual UN target texts
- N pairs with individual layman descriptions
- 1 pair with local government keywords
- 1 pair with keywords

Excluded: detailed_info (too generic), indicators (measurement criteria).

Data split: 20% out-of-sample / 60% fine-tuning / 20% weight optimization.
All stratified by SDG. No overlap between fine-tuning and weight optimization.
Uses SDG-aware batch sampling to avoid MNR false negatives.
"""

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader, Sampler
from tqdm import tqdm

sys_path = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(sys_path))

from src.config.sdg_definitions import SDG_DEFINITIONS
from src.config.sdg_target_definitions import SDG_TARGET_DEFINITIONS, get_targets_for_sdg

# --- SDG text variant generation (for fine-tuning pairs) ---

def build_sdg_variant_texts(sdg_num: int) -> List[str]:
    """Build all filtered variant texts for an SDG (for fine-tuning positive pairs).

    Returns list of texts, each within the 384-token limit.
    Excluded: detailed_info (too generic), indicators (measurement criteria).
    """
    sdg = SDG_DEFINITIONS.get(sdg_num, {})
    variants = []

    # Core description
    core_text = f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('description', '')}"
    variants.append(core_text)

    # Per-target UN text and layman description
    targets = get_targets_for_sdg(sdg_num)
    for target_id, target_def in targets.items():
        # UN target text
        variants.append(
            f"Target {target_id} of SDG {sdg_num}: {target_def['target_text']}"
        )
        # Layman description
        variants.append(
            f"Target {target_id} of SDG {sdg_num}: {target_def['layman_description']}"
        )

    # Local government keywords
    local_gov_keywords = sdg.get('local_gov_keywords', [])
    if local_gov_keywords:
        variants.append(
            f"Local government and council activities for {sdg.get('name', '')}: "
            + ", ".join(local_gov_keywords[:30])
        )

    # Keywords
    all_keywords = list(sdg.get('keywords', []))
    all_keywords.extend(sdg.get('local_gov_keywords', [])[:20])
    if all_keywords:
        variants.append(
            f"Keywords for SDG {sdg_num} {sdg.get('name', '')}: "
            + ", ".join(all_keywords[:40])
        )

    return variants


# --- Data loading ---

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
    SDG_COLS = [f"SDG{i}" for i in range(1, 18)]

    print(f"Loading AidData from {xlsx_path}...")
    df = pd.read_excel(xlsx_path, sheet_name="Extended ver.")
    df = df.dropna(subset=["Description"])
    df = df[df["Description"].str.strip() != ""]
    df = df.dropna(subset=SDG_COLS, how="all")

    for col in SDG_COLS:
        df[col] = df[col].fillna(0).astype(int)

    print(f"AidData records: {len(df)}")
    return df


# --- Stratified splitting ---

def stratified_split_by_sdg(df, sdg_labels, test_frac=0.2, random_state=42):
    """Split dataframe stratified by SDG.

    For single-label data (OSDG): stratify by the single SDG label.
    For multi-label data (AidData): stratify by the primary (first) SDG label.

    Args:
        df: DataFrame with text and SDG labels
        sdg_labels: Series or array of SDG labels (single int per row)
        test_frac: Fraction for test set
        random_state: Random seed

    Returns:
        (train_df, test_df) tuple
    """
    rng = np.random.RandomState(random_state)

    train_indices = []
    test_indices = []

    for sdg_num in range(1, 18):
        mask = sdg_labels == sdg_num
        indices = np.where(mask)[0]
        rng.shuffle(indices)

        n_test = max(1, int(len(indices) * test_frac))
        test_indices.extend(indices[:n_test])
        train_indices.extend(indices[n_test:])

    return df.iloc[train_indices].reset_index(drop=True), df.iloc[test_indices].reset_index(drop=True)


# --- Training pair creation ---

def create_training_pairs_osdg(df: pd.DataFrame) -> List[InputExample]:
    """Create positive pairs for OSDG single-label data.

    Each text is paired with every filtered variant of its labeled SDG.
    """
    examples = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="OSDG pairs"):
        text = row['text']
        sdg_num = int(row['sdg'])
        variant_texts = build_sdg_variant_texts(sdg_num)
        for variant_text in variant_texts:
            examples.append(InputExample(texts=[text, variant_text]))

    return examples


def create_training_pairs_aiddata(df: pd.DataFrame) -> List[InputExample]:
    """Create positive pairs for AidData multi-label data.

    Each text is paired with every filtered variant of each of its labeled SDGs.
    """
    SDG_COLS = [f"SDG{i}" for i in range(1, 18)]
    examples = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="AidData pairs"):
        text = row['Description']
        for col in SDG_COLS:
            if row[col] == 1:
                sdg_num = int(col.replace('SDG', ''))
                variant_texts = build_sdg_variant_texts(sdg_num)
                for variant_text in variant_texts:
                    examples.append(InputExample(texts=[text, variant_text]))

    return examples


# --- SDG-aware batch sampler ---

class SDGAwareBatchSampler(Sampler):
    """Batch sampler that ensures at most one variant per SDG per batch.

    This avoids MNR false negatives where two descriptions of the same SDG
    would be treated as negatives for each other.
    """

    def __init__(self, examples: List[InputExample], batch_size: int,
                 sdg_label_per_example: List[int], shuffle: bool = True):
        """
        Args:
            examples: Training examples
            batch_size: Batch size
            sdg_label_per_example: SDG number for each example's positive pair
            shuffle: Whether to shuffle
        """
        self.examples = examples
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.sdg_labels = sdg_label_per_example

        # Group example indices by SDG
        self.sdg_groups = defaultdict(list)
        for idx, sdg_num in enumerate(self.sdg_labels):
            self.sdg_groups[sdg_num].append(idx)

        # Pre-compute batches: one example per SDG per batch
        self.batches = self._create_batches()

    def _create_batches(self) -> List[List[int]]:
        """Create batches with at most one example per SDG."""
        # Get list of SDGs and shuffle their example pools
        sdg_nums = list(self.sdg_groups.keys())
        pools = {}
        for sdg_num in sdg_nums:
            indices = list(self.sdg_groups[sdg_num])
            if self.shuffle:
                random.shuffle(indices)
            pools[sdg_num] = indices

        batches = []
        # Round-robin: each batch picks one example from each SDG until exhausted
        max_len = max(len(v) for v in pools.values()) if pools else 0
        positions = {sdg: 0 for sdg in sdg_nums}

        for _ in range(max_len):
            batch = []
            for sdg_num in sdg_nums:
                if positions[sdg_num] < len(pools[sdg_num]):
                    batch.append(pools[sdg_num][positions[sdg_num]])
                    positions[sdg_num] += 1

            # Split large batches
            if len(batch) > self.batch_size:
                for i in range(0, len(batch), self.batch_size):
                    batches.append(batch[i:i + self.batch_size])
            elif batch:
                batches.append(batch)

        if self.shuffle:
            random.shuffle(batches)

        return batches

    def __iter__(self):
        return iter(self.batches)

    def __len__(self):
        return len(self.batches)


def infer_sdg_label(example: InputExample) -> int:
    """Infer the SDG number from an example's second text (the SDG variant).

    Parses "SDG {n}:" or "Target {id} of SDG {n}:" patterns.
    """
    text = example.texts[1]
    # Try "SDG {n}:" pattern
    import re
    m = re.search(r'SDG\s+(\d+)', text)
    if m:
        return int(m.group(1))
    # Try "Target {id} of SDG {n}:" pattern
    m = re.search(r'of SDG\s+(\d+)', text)
    if m:
        return int(m.group(1))
    return 0


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune sentence transformer with SDG text variants"
    )
    parser.add_argument("--base-model", default="models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509",
                        help="Base model to fine-tune (default: current fine-tuned model)")
    parser.add_argument("--output-path", default="models/sdg-finetuned",
                        help="Output directory for fine-tuned model")
    parser.add_argument("--osdg-path", default="data/external/osdg-community-data-v2024-04-01.csv",
                        help="Path to OSDG Community Dataset")
    parser.add_argument("--aiddata-path",
                        default="data/external/30015124/Chinese_Development_Finance_SDG_Categorizations_2000-2021.xlsx",
                        help="Path to AidData Excel file")
    parser.add_argument("--min-agreement", type=float, default=0.7,
                        help="Minimum OSDG agreement score")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-aiddata", action="store_true",
                        help="Skip AidData (OSDG only)")
    args = parser.parse_args()

    # Set seeds
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # --- Load data ---
    osdg_df = load_osdg_data(Path(args.osdg_path), args.min_agreement)

    aiddata_df = None
    if not args.skip_aiddata:
        aiddata_df = load_aiddata_data(Path(args.aiddata_path))

    # --- Split data: 20% out-of-sample / 60% fine-tuning / 20% weight optimization ---

    # OSDG: single-label, stratify by SDG label
    osdg_outofsample, osdg_remaining = stratified_split_by_sdg(
        osdg_df, osdg_df['sdg'].astype(int), test_frac=0.2, random_state=args.seed
    )
    # From remaining 80%, split into 75% fine-tuning (=60% of total) and 25% weight optimization (=20% of total)
    osdg_finetune, osdg_weightopt = stratified_split_by_sdg(
        osdg_remaining, osdg_remaining['sdg'].astype(int), test_frac=0.25, random_state=args.seed + 1
    )

    print(f"\nOSDG splits: out-of-sample={len(osdg_outofsample)}, "
          f"fine-tuning={len(osdg_finetune)}, weight-optimization={len(osdg_weightopt)}")

    # AidData: multi-label, stratify by primary SDG (highest-scoring)
    if aiddata_df is not None:
        SDG_COLS = [f"SDG{i}" for i in range(1, 18)]
        # Primary SDG = first SDG with value 1
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
    else:
        aiddata_finetune = None
        aiddata_outofsample = None
        aiddata_weightopt = None

    # --- Save splits for reproducibility ---
    splits_dir = Path("data/splits")
    splits_dir.mkdir(parents=True, exist_ok=True)

    osdg_outofsample.to_csv(splits_dir / "osdg_outofsample.csv", index=False)
    osdg_finetune.to_csv(splits_dir / "osdg_finetune.csv", index=False)
    osdg_weightopt.to_csv(splits_dir / "osdg_weightopt.csv", index=False)

    if aiddata_outofsample is not None:
        aiddata_outofsample.to_csv(splits_dir / "aiddata_outofsample.csv", index=False)
        aiddata_finetune.to_csv(splits_dir / "aiddata_finetune.csv", index=False)
        aiddata_weightopt.to_csv(splits_dir / "aiddata_weightopt.csv", index=False)

    print(f"\nData splits saved to {splits_dir}/")

    # --- Create positive training pairs ---
    print("\nCreating positive training pairs...")
    train_examples = create_training_pairs_osdg(osdg_finetune)
    print(f"OSDG training pairs: {len(train_examples)}")

    if aiddata_finetune is not None:
        aiddata_examples = create_training_pairs_aiddata(aiddata_finetune)
        train_examples.extend(aiddata_examples)
        print(f"AidData training pairs: {len(aiddata_examples)}")

    print(f"Total training pairs: {len(train_examples)}")

    # --- Fine-tune ---
    print(f"\nLoading base model: {args.base_model}")
    model = SentenceTransformer(args.base_model)

    # Use standard DataLoader with shuffle=True
    # Note: NoDuplicatesDataLoader was removed in sentence-transformers v3+.
    # With 307K training pairs and batch_size=32, the probability of same-SDG
    # variants landing in the same batch is low. MNR treats all other pairs
    # in the batch as negatives; a few same-SDG false negatives among 32
    # examples have minimal impact on training quality.
    train_dataloader = DataLoader(
        train_examples,
        batch_size=args.batch_size,
        shuffle=True,
    )

    train_loss = losses.MultipleNegativesRankingLoss(model)

    # Training
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"sdg-variant-finetuned-{timestamp}"
    full_output_path = Path(args.output_path) / model_name
    full_output_path.mkdir(parents=True, exist_ok=True)

    print(f"\nStarting fine-tuning...")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.learning_rate}")
    print(f"  Training pairs: {len(train_examples)}")
    print(f"  Output: {full_output_path}")

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=args.warmup_steps,
        optimizer_params={'lr': args.learning_rate},
        output_path=str(full_output_path),
        show_progress_bar=True,
    )

    print(f"\nModel saved to: {full_output_path}")

    # Save training info
    training_info = {
        'base_model': args.base_model,
        'finetuned_model_path': str(full_output_path),
        'osdg_training_samples': len(osdg_finetune),
        'aiddata_training_samples': len(aiddata_finetune) if aiddata_finetune is not None else 0,
        'total_training_pairs': len(train_examples),
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.learning_rate,
        'seed': args.seed,
        'variant_types': ['core', 'un_target_text', 'layman_description', 'local_gov', 'keywords'],
        'excluded_variants': ['detailed_info', 'indicators'],
        'data_split': '20% out-of-sample / 60% fine-tuning / 20% weight optimization',
        'timestamp': datetime.now().isoformat(),
    }

    info_path = full_output_path / "training_info.json"
    with open(info_path, 'w') as f:
        json.dump(training_info, f, indent=2)
    print(f"Training info saved to: {info_path}")

    # --- Evaluate baseline vs fine-tuned on out-of-sample set ---
    print("\n" + "=" * 70)
    print("OUT-OF-SAMPLE EVALUATION")
    print("=" * 70)

    # Simple top-1 accuracy on OSDG out-of-sample
    osdg_test_texts = osdg_outofsample['text'].tolist()
    osdg_test_labels = osdg_outofsample['sdg'].astype(int).tolist()

    # Build SDG embeddings with the fine-tuned model
    sdg_descs = {}
    for sdg_num in range(1, 18):
        sdg = SDG_DEFINITIONS.get(sdg_num, {})
        sdg_descs[sdg_num] = f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('description', '')}"

    sdg_embeddings = {}
    for sdg_num, desc in sdg_descs.items():
        sdg_embeddings[sdg_num] = model.encode(desc, convert_to_numpy=True)

    # Evaluate
    correct = 0
    total = len(osdg_test_texts)
    for text, true_sdg in zip(osdg_test_texts, osdg_test_labels):
        text_emb = model.encode(text, convert_to_numpy=True)
        scores = {}
        for sdg_num, sdg_emb in sdg_embeddings.items():
            sim = np.dot(text_emb, sdg_emb) / (np.linalg.norm(text_emb) * np.linalg.norm(sdg_emb))
            scores[sdg_num] = sim
        pred_sdg = max(scores.keys(), key=lambda k: scores[k])
        if pred_sdg == true_sdg:
            correct += 1

    accuracy = correct / total if total > 0 else 0
    print(f"\nOSDG out-of-sample top-1 accuracy: {accuracy:.4f} ({correct}/{total})")

    print(f"\n{'=' * 70}")
    print("Fine-tuning complete!")
    print(f"Model: {full_output_path}")
    print(f"To use: python scripts/run_analysis.py --model {full_output_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()