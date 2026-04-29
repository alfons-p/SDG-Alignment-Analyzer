#!/usr/bin/env python3
"""Fine-tune sentence transformer on OSDG data for SDG classification.

This script fine-tunes a sentence transformer model using the OSDG Community Dataset
to improve SDG classification accuracy.
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
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader
from tqdm import tqdm


# SDG Definitions for reference
SDG_DEFINITIONS = {
    1: {"name": "No Poverty", "keywords": ["poverty", "income", "welfare", "social protection"]},
    2: {"name": "Zero Hunger", "keywords": ["hunger", "food security", "nutrition", "agriculture"]},
    3: {"name": "Good Health and Well-being", "keywords": ["health", "well-being", "healthcare"]},
    4: {"name": "Quality Education", "keywords": ["education", "learning", "training", "skills"]},
    5: {"name": "Gender Equality", "keywords": ["gender equality", "women empowerment"]},
    6: {"name": "Clean Water and Sanitation", "keywords": ["water", "sanitation", "wastewater"]},
    7: {"name": "Affordable and Clean Energy", "keywords": ["energy", "renewable energy", "solar"]},
    8: {"name": "Decent Work and Economic Growth", "keywords": ["employment", "economic growth", "jobs"]},
    9: {"name": "Industry, Innovation and Infrastructure", "keywords": ["infrastructure", "innovation"]},
    10: {"name": "Reduced Inequalities", "keywords": ["inequality", "equity", "social inclusion"]},
    11: {"name": "Sustainable Cities and Communities", "keywords": ["urban planning", "cities", "housing"]},
    12: {"name": "Responsible Consumption and Production", "keywords": ["sustainable consumption", "recycling"]},
    13: {"name": "Climate Action", "keywords": ["climate change", "carbon emissions"]},
    14: {"name": "Life Below Water", "keywords": ["marine", "oceans", "waterways"]},
    15: {"name": "Life on Land", "keywords": ["biodiversity", "ecosystems", "forests"]},
    16: {"name": "Peace, Justice and Strong Institutions", "keywords": ["governance", "transparency"]},
    17: {"name": "Partnerships for the Goals", "keywords": ["partnership", "collaboration"]},
}


def set_seed(seed: int = 42):
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_osdg_data(csv_path: Path, min_agreement: float = 0.7):
    """Load OSDG data with quality filtering."""
    print(f"Loading OSDG data from {csv_path}...")

    try:
        df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')
    except TypeError:
        df = pd.read_csv(csv_path, sep='\t', error_bad_lines=False)

    print(f"Total records: {len(df)}")

    # Filter by agreement
    df = df[df['agreement'] >= min_agreement].copy()
    print(f"Records with agreement >= {min_agreement}: {len(df)}")

    # Remove empty text
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]
    print(f"Records with valid text: {len(df)}")

    # Filter to valid SDGs (1-17)
    df = df[df['sdg'].isin(range(1, 18))]
    print(f"Records with valid SDG labels: {len(df)}")

    return df


def prepare_training_data(df, max_samples_per_sdg=1000, min_samples_per_sdg=50):
    """
    Prepare training and validation data.

    Strategy: Use MultipleNegativesRankingLoss with (text, SDG_description) pairs.
    Positive pairs: text + its labeled SDG description
    """
    print("\nPreparing training data...")

    # Create SDG descriptions
    sdg_descriptions = {}
    for sdg_num in range(1, 18):
        sdg = SDG_DEFINITIONS[sdg_num]
        sdg_descriptions[sdg_num] = f"SDG {sdg_num}: {sdg['name']}. Keywords: {', '.join(sdg['keywords'])}"

    # Group by SDG
    sdg_groups = defaultdict(list)
    for _, row in df.iterrows():
        sdg_groups[int(row['sdg'])].append(row['text'])

    # Balance dataset
    train_examples = []
    val_examples = []

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

        sdg_desc = sdg_descriptions[sdg_num]

        # Create training examples
        for text in train_texts:
            train_examples.append(InputExample(texts=[text, sdg_desc]))

        # Create validation examples
        for text in val_texts:
            val_examples.append(InputExample(texts=[text, sdg_desc]))

    print(f"Training examples: {len(train_examples)}")
    print(f"Validation examples: {len(val_examples)}")

    return train_examples, val_examples


def finetune_model(train_examples, val_examples, base_model="all-mpnet-base-v2",
                   output_path="models/sdg-finetuned", epochs=3, batch_size=32,
                   learning_rate=2e-5, warmup_steps=100, evaluation_steps=1000):
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
        name='osdg-val',
        show_progress_bar=True
    )

    # Training parameters
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"sdg-finetuned-{timestamp}"
    full_output_path = output_path / model_name

    print(f"\nStarting fine-tuning...")
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


def evaluate_finetuned_model(model_path, test_df, sample_size=500):
    """Evaluate the fine-tuned model against OSDG labels."""

    print(f"\nEvaluating model: {model_path}")
    model = SentenceTransformer(model_path)

    # Sample test data
    if len(test_df) > sample_size:
        test_df = test_df.sample(n=sample_size, random_state=42)

    # Create SDG embeddings
    sdg_embeddings = {}
    for sdg_num in range(1, 18):
        sdg = SDG_DEFINITIONS[sdg_num]
        text = f"SDG {sdg_num}: {sdg['name']}. Keywords: {', '.join(sdg['keywords'])}"
        sdg_embeddings[sdg_num] = model.encode(text, convert_to_numpy=True)

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
    """Compare baseline vs fine-tuned model."""

    print("\n" + "="*70)
    print("MODEL COMPARISON: Baseline vs Fine-Tuned")
    print("="*70)

    # Evaluate baseline
    print("\n1. Evaluating BASELINE model...")
    baseline_eval = evaluate_finetuned_model(base_model_name, test_df, sample_size)

    # Evaluate fine-tuned
    print("\n2. Evaluating FINE-TUNED model...")
    finetuned_eval = evaluate_finetuned_model(finetuned_model_path, test_df, sample_size)

    # Compare results
    print("\n" + "="*70)
    print("COMPARISON RESULTS")
    print("="*70)

    print(f"\n{'Metric':<30} {'Baseline':<15} {'Fine-Tuned':<15} {'Improvement':<15}")
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
    print(f"{'SDG':<5} {'Name':<35} {'Baseline':<10} {'Fine-Tuned':<10} {'Change':<10}")
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
        description="Fine-tune sentence transformer on OSDG data"
    )
    parser.add_argument("--base-model", default="all-mpnet-base-v2",
                        help="Base model to fine-tune")
    parser.add_argument("--output-path", default="models/sdg-finetuned",
                        help="Output directory for fine-tuned model")
    parser.add_argument("--min-agreement", type=float, default=0.7,
                        help="Minimum OSDG agreement score")
    parser.add_argument("--max-samples-per-sdg", type=int, default=1000,
                        help="Maximum samples per SDG")
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

    # Check for OSDG data
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    if not csv_path.exists():
        print(f"Error: OSDG data not found at {csv_path}")
        print("Download from: https://zenodo.org/records/11441197")
        return

    # Load data
    df = load_osdg_data(csv_path, min_agreement=args.min_agreement)

    if len(df) == 0:
        print("No data loaded. Exiting.")
        return

    # Prepare training data
    train_examples, val_examples = prepare_training_data(
        df, max_samples_per_sdg=args.max_samples_per_sdg
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
    )

    # Save training info
    training_info = {
        'base_model': args.base_model,
        'finetuned_model_path': model_path,
        'training_samples': len(train_examples),
        'validation_samples': len(val_examples),
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.learning_rate,
        'timestamp': datetime.now().isoformat(),
    }

    info_path = Path(model_path) / "training_info.json"
    with open(info_path, 'w') as f:
        json.dump(training_info, f, indent=2)
    print(f"\nTraining info saved to: {info_path}")

    # Compare with baseline
    if not args.skip_comparison:
        test_df = df.sample(n=min(args.eval_sample_size, len(df)), random_state=123)
        compare_models(args.base_model, model_path, test_df, args.eval_sample_size)

    print(f"\n{'='*70}")
    print("Fine-tuning complete!")
    print(f"Model: {model_path}")
    print(f"\nTo use: python scripts/run_analysis.py --model {model_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
