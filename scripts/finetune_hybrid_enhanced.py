#!/usr/bin/env python3
"""Fine-tune sentence transformer on hybrid data with enhanced SDG embeddings.

This script combines:
1. Hybrid data sources: OSDG Community Dataset + Chinese LLM labeled data
2. Enhanced SDG definitions: multi-text embeddings with local government keywords and UN indicators

Usage:
    # Default hybrid + enhanced training
    python scripts/finetune_hybrid_enhanced.py

    # With custom thresholds
    python scripts/finetune_hybrid_enhanced.py --min-agreement 0.7 --chinese-llm-min-agreement 0.67
"""

import argparse
import json
import random
import pickle
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader
from tqdm import tqdm
import sys

# Add src to path for enhanced config
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import SDG_DEFINITIONS

# Default paths for each data source
DATA_SOURCES = {
    'osdg': 'data/external/osdg-community-data-v2024-04-01.csv',
    'chinese_llm': 'data/processed/chinese_llm_ft_labels.tsv',
}


def set_seed(seed: int = 42):
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def generate_sdg_text_variants(sdg_num: int) -> Dict[str, str]:
    """
    Generate multiple text variants for SDG embedding.

    This creates richer training targets by encoding different aspects
    of each SDG separately.
    """
    sdg = SDG_DEFINITIONS.get(sdg_num, {})

    variants = {}

    # Variant 1: Core description
    core_text = f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('description', '')}"
    variants['core'] = core_text

    # Variant 2: Local government context
    local_gov_keywords = sdg.get('local_gov_keywords', [])
    if local_gov_keywords:
        local_text = f"Local government activities for {sdg.get('name', '')}: " + ", ".join(local_gov_keywords[:30])
        variants['local_gov'] = local_text
    else:
        variants['local_gov'] = core_text

    # Variant 3: UN indicators
    indicators = sdg.get('indicators', [])
    if indicators:
        indicator_text = f"UN SDG {sdg_num} indicators: " + ", ".join(indicators[:5])
        variants['indicators'] = indicator_text
    else:
        variants['indicators'] = core_text

    # Variant 4: Keywords focus
    all_keywords = []
    all_keywords.extend(sdg.get('keywords', []))
    all_keywords.extend(sdg.get('local_gov_keywords', [])[:20])

    if all_keywords:
        keyword_text = f"SDG {sdg_num} {sdg.get('name', '')} keywords: " + ", ".join(all_keywords[:40])
        variants['keywords'] = keyword_text
    else:
        variants['keywords'] = core_text

    return variants


def combine_embeddings(embeddings: Dict[str, np.ndarray]) -> np.ndarray:
    """Combine multiple embeddings using weighted average."""
    weights = {
        'core': 0.35,
        'local_gov': 0.30,
        'indicators': 0.15,
        'keywords': 0.20
    }

    total_weight = sum(weights.get(k, 0.25) for k in embeddings.keys())

    combined = np.zeros_like(list(embeddings.values())[0])
    for variant, emb in embeddings.items():
        weight = weights.get(variant, 0.25) / total_weight
        combined += weight * emb

    # Normalize
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm

    return combined


def create_enhanced_sdg_embeddings(model: SentenceTransformer) -> Dict[int, np.ndarray]:
    """
    Create enhanced SDG embeddings using multi-text approach.

    Args:
        model: The sentence transformer model to use for encoding

    Returns:
        Dictionary mapping SDG numbers to combined embeddings
    """
    print("\nGenerating enhanced SDG embeddings for fine-tuning...")
    print("Using multi-text strategy (core + local_gov + indicators + keywords)")

    sdg_embeddings = {}

    for sdg_num in range(1, 18):
        # Generate text variants
        text_variants = generate_sdg_text_variants(sdg_num)

        # Encode each variant
        variant_embeddings = {}
        for variant_name, text in text_variants.items():
            embedding = model.encode(text, convert_to_numpy=True)
            variant_embeddings[variant_name] = embedding

        # Combine embeddings
        combined_embedding = combine_embeddings(variant_embeddings)
        sdg_embeddings[sdg_num] = combined_embedding

        if sdg_num % 5 == 0:
            print(f"  Generated embeddings for {sdg_num}/17 SDGs...")

    print(f"Generated enhanced embeddings for all 17 SDGs")
    return sdg_embeddings


def load_sdg_data(csv_path: Path, min_agreement: float = 0.7, source_name: str = "data"):
    """Load SDG labeled data with quality filtering.

    Works with both OSDG format and Chinese LLM labeled data.
    Both should have columns: text, sdg, agreement
    """
    print(f"Loading {source_name} from {csv_path}...")

    try:
        df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')
    except TypeError:
        df = pd.read_csv(csv_path, sep='\t', error_bad_lines=False)

    print(f"  Total records: {len(df)}")

    # Filter by agreement
    df = df[df['agreement'] >= min_agreement].copy()
    print(f"  Records with agreement >= {min_agreement}: {len(df)}")

    # Remove empty text
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]
    print(f"  Records with valid text: {len(df)}")

    # Filter to valid SDGs (1-17)
    df = df[df['sdg'].isin(range(1, 18))]
    print(f"  Records with valid SDG labels: {len(df)}")

    # Add source column for tracking
    df['source'] = source_name

    return df


def load_hybrid_data(osdg_path: Path, chinese_llm_path: Path,
                     osdg_min_agreement: float = 0.7,
                     chinese_llm_min_agreement: float = 0.67):
    """Load and combine OSDG and Chinese LLM labeled data."""
    print("\n" + "="*70)
    print("Loading HYBRID dataset (OSDG + Chinese LLM)")
    print("="*70)

    dfs = []

    # Load OSDG data
    if osdg_path.exists():
        df_osdg = load_sdg_data(osdg_path, osdg_min_agreement, "OSDG")
        dfs.append(df_osdg)
    else:
        print(f"Warning: OSDG data not found at {osdg_path}")

    # Load Chinese LLM data
    if chinese_llm_path.exists():
        df_chinese = load_sdg_data(chinese_llm_path, chinese_llm_min_agreement, "Chinese LLM")
        dfs.append(df_chinese)
    else:
        print(f"Warning: Chinese LLM data not found at {chinese_llm_path}")

    if not dfs:
        raise ValueError("No data sources found!")

    # Combine datasets
    df_combined = pd.concat(dfs, ignore_index=True)
    print(f"\nCombined dataset: {len(df_combined)} total records")

    # Print per-SDG distribution
    print("\nPer-SDG distribution:")
    for sdg_num in range(1, 18):
        count = len(df_combined[df_combined['sdg'] == sdg_num])
        print(f"  SDG {sdg_num:2d}: {count:5d} samples")

    return df_combined


def prepare_training_data(df, max_samples_per_sdg=1000, min_samples_per_sdg=50):
    """
    Prepare training and validation data using enhanced SDG definitions.

    Creates training pairs: (text, enhanced_sdg_description)
    """
    print("\nPreparing training data with enhanced SDG definitions...")

    train_examples = []
    val_examples = []

    # Group by SDG
    sdg_groups = defaultdict(list)
    for _, row in df.iterrows():
        sdg_groups[int(row['sdg'])].append(row['text'])

    for sdg_num in range(1, 18):
        texts = sdg_groups[sdg_num]

        if len(texts) < min_samples_per_sdg:
            print(f"Warning: SDG {sdg_num} has only {len(texts)} samples (min: {min_samples_per_sdg})")
            continue

        # Sample if too many
        if len(texts) > max_samples_per_sdg:
            texts = random.sample(texts, max_samples_per_sdg)

        # Split train/val (80/20)
        split_idx = int(len(texts) * 0.8)
        train_texts = texts[:split_idx]
        val_texts = texts[split_idx:]

        # Create enhanced target text using SDG definitions
        sdg = SDG_DEFINITIONS[sdg_num]
        target_text = (f"SDG {sdg_num}: {sdg['name']}. "
                      f"Local activities: {', '.join(sdg.get('local_gov_keywords', [])[:15])}")

        for text in train_texts:
            train_examples.append(InputExample(texts=[text, target_text]))

        for text in val_texts:
            val_examples.append(InputExample(texts=[text, target_text]))

    print(f"Training examples: {len(train_examples)}")
    print(f"Validation examples: {len(val_examples)}")

    return train_examples, val_examples


def finetune_model(train_examples, val_examples, base_model="all-mpnet-base-v2",
                   output_path="models/sdg-finetuned", epochs=3, batch_size=32,
                   learning_rate=2e-5, warmup_steps=100, evaluation_steps=1000,
                   model_suffix="hybrid_enhanced"):
    """Fine-tune the sentence transformer model."""

    print(f"\nLoading base model: {base_model}")
    model = SentenceTransformer(base_model)

    # Create dataloader
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)

    # Use MultipleNegativesRankingLoss for training
    train_loss = losses.MultipleNegativesRankingLoss(model)

    # Create evaluator for validation
    val_sentences1 = [ex.texts[0] for ex in val_examples]
    val_sentences2 = [ex.texts[1] for ex in val_examples]
    val_scores = [1.0] * len(val_examples)

    evaluator = EmbeddingSimilarityEvaluator(
        val_sentences1, val_sentences2, val_scores,
        name='hybrid-enhanced-val',
        show_progress_bar=True
    )

    # Training parameters
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"sdg-{model_suffix}-{timestamp}"
    full_output_path = output_path / model_name

    print(f"\nStarting hybrid-enhanced fine-tuning...")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Learning rate: {learning_rate}")
    print(f"  Output: {full_output_path}")

    # Train the model
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        evaluator=evaluator,
        epochs=epochs,
        evaluation_steps=evaluation_steps,
        warmup_steps=warmup_steps,
        optimizer_params={'lr': learning_rate},
        output_path=str(full_output_path),
        show_progress_bar=True,
    )

    print(f"\nModel saved to: {full_output_path}")
    return str(full_output_path)


def evaluate_with_embeddings(model_path, sdg_embeddings: Dict[int, np.ndarray],
                              test_df, sample_size=500):
    """Evaluate the fine-tuned model against SDG labels."""

    print(f"\nEvaluating model: {model_path}")
    model = SentenceTransformer(model_path)

    # Sample test data
    if len(test_df) > sample_size:
        test_df = test_df.sample(n=sample_size, random_state=42)

    # Evaluate
    results = []
    correct = 0
    sdg_stats = defaultdict(lambda: {'correct': 0, 'total': 0})

    print(f"Evaluating {len(test_df)} samples...")

    for _, row in tqdm(test_df.iterrows(), total=len(test_df)):
        text = row['text']
        true_sdg = int(row['sdg'])

        text_embedding = model.encode(text, convert_to_numpy=True)

        scores = {}
        for sdg_num, sdg_emb in sdg_embeddings.items():
            # Cosine similarity
            sim = np.dot(text_embedding, sdg_emb) / (np.linalg.norm(text_embedding) * np.linalg.norm(sdg_emb))
            scores[sdg_num] = sim

        pred_sdg = max(scores.keys(), key=lambda k: scores[k])
        pred_score = scores[pred_sdg]

        is_correct = pred_sdg == true_sdg
        if is_correct:
            correct += 1

        sdg_stats[true_sdg]['total'] += 1
        if is_correct:
            sdg_stats[true_sdg]['correct'] += 1

        results.append({
            'true_sdg': true_sdg,
            'predicted_sdg': pred_sdg,
            'predicted_score': pred_score,
            'correct': is_correct,
        })

    total = len(results)
    accuracy = correct / total if total > 0 else 0

    sdg_accuracies = {}
    for sdg_num in range(1, 18):
        stats = sdg_stats[sdg_num]
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        sdg_accuracies[sdg_num] = {
            'accuracy': acc,
            'correct': stats['correct'],
            'total': stats['total']
        }

    return {
        'total': total,
        'correct': correct,
        'accuracy': accuracy,
        'sdg_accuracies': sdg_accuracies,
    }


def compare_models(base_model_name, finetuned_model_path, test_df, sample_size=500):
    """Compare baseline vs fine-tuned model using enhanced embeddings."""

    print("\n" + "="*70)
    print("MODEL COMPARISON: Baseline vs Hybrid-Enhanced Fine-Tuned")
    print("="*70)

    # Create enhanced embeddings for baseline model
    print("\nGenerating enhanced embeddings for baseline model...")
    base_model = SentenceTransformer(base_model_name)
    base_sdg_embeddings = create_enhanced_sdg_embeddings(base_model)

    # Create enhanced embeddings for fine-tuned model
    print("\nGenerating enhanced embeddings for fine-tuned model...")
    ft_model = SentenceTransformer(finetuned_model_path)
    ft_sdg_embeddings = create_enhanced_sdg_embeddings(ft_model)

    # Evaluate baseline
    print("\n1. Evaluating BASELINE model...")
    baseline_eval = evaluate_with_embeddings(base_model_name, base_sdg_embeddings, test_df, sample_size)

    # Evaluate fine-tuned
    print("\n2. Evaluating HYBRID-ENHANCED model...")
    finetuned_eval = evaluate_with_embeddings(finetuned_model_path, ft_sdg_embeddings, test_df, sample_size)

    # Compare results
    print("\n" + "="*70)
    print("COMPARISON RESULTS")
    print("="*70)

    print(f"\n{'Metric':<30} {'Baseline':<15} {'Hybrid-Enhanced':<15} {'Improvement':<15}")
    print("-"*70)

    base_acc = baseline_eval['accuracy']
    ft_acc = finetuned_eval['accuracy']
    improvement = ft_acc - base_acc
    improvement_pct = (improvement / base_acc) * 100 if base_acc > 0 else 0

    print(f"{'Overall Accuracy':<30} {base_acc:>14.2%} {ft_acc:>14.2%} {improvement:>+13.2%} ({improvement_pct:+.1f}%)")

    # Per-SDG comparison
    print("\n" + "-"*70)
    print("PER-SDG ACCURACY COMPARISON")
    print("-"*70)
    print(f"{'SDG':<5} {'Name':<35} {'Baseline':<10} {'Hybrid-Enh':<10} {'Change':<10}")
    print("-"*70)

    improvements = []
    for sdg_num in range(1, 18):
        base_sdg = baseline_eval['sdg_accuracies'][sdg_num]
        ft_sdg = finetuned_eval['sdg_accuracies'][sdg_num]

        if base_sdg['total'] > 0:
            name = SDG_DEFINITIONS[sdg_num]['name'][:34]
            base_acc_sdg = base_sdg['accuracy']
            ft_acc_sdg = ft_sdg['accuracy']
            delta = ft_acc_sdg - base_acc_sdg

            improvements.append((sdg_num, delta, ft_acc_sdg))

            marker = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else " ")
            print(f"{sdg_num:<5} {name:<35} {base_acc_sdg:>9.1%} {ft_acc_sdg:>9.1%} {delta:>+9.1%} {marker}")

    # Show biggest improvements
    print("\n" + "-"*70)
    print("BIGGEST IMPROVEMENTS")
    print("-"*70)
    improvements.sort(key=lambda x: x[1], reverse=True)
    for sdg_num, delta, acc in improvements[:5]:
        if delta > 0:
            name = SDG_DEFINITIONS[sdg_num]['name']
            print(f"  SDG {sdg_num} ({name}): +{delta:.1%} (now {acc:.1%})")

    print("\n" + "="*70)

    return baseline_eval, finetuned_eval


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune sentence transformer with hybrid data and enhanced SDG definitions"
    )
    parser.add_argument("--osdg-path", default=None,
                        help="Path to OSDG data (default: data/external/osdg-community-data-v2024-04-01.csv)")
    parser.add_argument("--chinese-llm-path", default=None,
                        help="Path to Chinese LLM labeled data (default: data/processed/chinese_llm_ft_labels.tsv)")
    parser.add_argument("--base-model", default="all-mpnet-base-v2",
                        help="Base model to fine-tune")
    parser.add_argument("--output-path", default="models/sdg-finetuned",
                        help="Output directory for fine-tuned model")
    parser.add_argument("--min-agreement", type=float, default=0.7,
                        help="Minimum agreement score for OSDG data (default: 0.7)")
    parser.add_argument("--chinese-llm-min-agreement", type=float, default=0.67,
                        help="Minimum agreement score for Chinese LLM data (default: 0.67)")
    parser.add_argument("--max-samples-per-sdg", type=int, default=1000,
                        help="Maximum samples per SDG")
    parser.add_argument("--min-samples-per-sdg", type=int, default=10,
                        help="Minimum samples per SDG (SDGs with fewer samples are skipped)")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Training batch size")
    parser.add_argument("--learning-rate", type=float, default=2e-5,
                        help="Learning rate")
    parser.add_argument("--eval-sample-size", type=int, default=500,
                        help="Sample size for evaluation")
    parser.add_argument("--skip-comparison", action="store_true",
                        help="Skip comparison with baseline")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")

    args = parser.parse_args()

    set_seed(args.seed)

    # Set paths
    osdg_path = Path(args.osdg_path) if args.osdg_path else Path(DATA_SOURCES['osdg'])
    chinese_llm_path = Path(args.chinese_llm_path) if args.chinese_llm_path else Path(DATA_SOURCES['chinese_llm'])

    print("\n" + "="*70)
    print("HYBRID-ENHANCED SDG FINE-TUNING")
    print("="*70)
    print("\nThis script fine-tunes using:")
    print("  - OSDG Community Dataset (~43,000 labeled texts)")
    print("  - Chinese LLM labeled data (council report labels)")
    print("  - Enhanced SDG definitions (936 local gov keywords)")
    print("  - Multi-text embeddings (4 variants combined)")
    print("  - 95 UN indicators integrated")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  OSDG path: {osdg_path}")
    print(f"  Chinese LLM path: {chinese_llm_path}")
    print(f"  OSDG min agreement: {args.min_agreement}")
    print(f"  Chinese LLM min agreement: {args.chinese_llm_min_agreement}")
    print(f"  Min samples per SDG: {args.min_samples_per_sdg}")
    print(f"  Max samples per SDG: {args.max_samples_per_sdg}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print("="*70)

    # Load hybrid data
    df = load_hybrid_data(
        osdg_path, chinese_llm_path,
        osdg_min_agreement=args.min_agreement,
        chinese_llm_min_agreement=args.chinese_llm_min_agreement
    )

    if len(df) == 0:
        print("No data loaded. Exiting.")
        return

    # Prepare training data with enhanced SDG definitions
    train_examples, val_examples = prepare_training_data(
        df, max_samples_per_sdg=args.max_samples_per_sdg,
        min_samples_per_sdg=args.min_samples_per_sdg
    )

    if len(train_examples) == 0:
        print("No training examples. Exiting.")
        return

    # Fine-tune model
    model_path = finetune_model(
        train_examples=train_examples,
        val_examples=val_examples,
        base_model=args.base_model,
        output_path=args.output_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        model_suffix="hybrid_enhanced",
    )

    # Load base model and create enhanced embeddings for evaluation
    print("\nCreating enhanced SDG embeddings for evaluation...")
    base_model = SentenceTransformer(args.base_model)
    sdg_embeddings = create_enhanced_sdg_embeddings(base_model)

    # Save training info
    training_info = {
        'base_model': args.base_model,
        'finetuned_model_path': model_path,
        'data_sources': ['OSDG', 'Chinese LLM'],
        'training_samples': len(train_examples),
        'validation_samples': len(val_examples),
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.learning_rate,
        'min_agreement': args.min_agreement,
        'chinese_llm_min_agreement': args.chinese_llm_min_agreement,
        'min_samples_per_sdg': args.min_samples_per_sdg,
        'max_samples_per_sdg': args.max_samples_per_sdg,
        'enhanced_embeddings': True,
        'sdg_definitions_version': 'enhanced_v2',
        'features': [
            'hybrid_data_osdg_chinese_llm',
            'multi_text_embeddings',
            'local_gov_keywords',
            'un_indicators',
            'weighted_combination'
        ],
        'timestamp': datetime.now().isoformat(),
    }

    info_path = Path(model_path) / "training_info.json"
    with open(info_path, 'w') as f:
        json.dump(training_info, f, indent=2)
    print(f"\nTraining info saved to: {info_path}")

    # Save enhanced embeddings
    embeddings_path = Path(model_path) / "enhanced_sdg_embeddings.pkl"
    with open(embeddings_path, 'wb') as f:
        pickle.dump(sdg_embeddings, f)
    print(f"Enhanced SDG embeddings saved to: {embeddings_path}")

    # Compare with baseline
    if not args.skip_comparison:
        test_df = df.sample(n=min(args.eval_sample_size, len(df)), random_state=123)
        compare_models(args.base_model, model_path, test_df, args.eval_sample_size)

    print(f"\n{'='*70}")
    print("Hybrid-Enhanced fine-tuning complete!")
    print(f"Model: {model_path}")
    print(f"\nTo use: python scripts/run_analysis.py --model {model_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()