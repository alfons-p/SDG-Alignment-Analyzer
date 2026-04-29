#!/usr/bin/env python3
"""Standalone OSDG evaluation without full project dependencies.

This script evaluates sentence transformer models against OSDG labels
using only the sentence-transformers library.
"""

import sys
from pathlib import Path
from typing import Dict, List
import json
from collections import defaultdict

import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer


# SDG Definitions (copied from config.py for standalone use)
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


class SimpleSDGEvaluator:
    """Simple SDG evaluator using sentence transformers."""

    def __init__(self, model_name: str = "all-mpnet-base-v2", threshold: float = 0.3):
        """Initialize evaluator with model."""
        print(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.sdg_embeddings = self._compute_sdg_embeddings()

    def _compute_sdg_embeddings(self) -> Dict[int, np.ndarray]:
        """Pre-compute embeddings for all SDGs."""
        sdg_embeddings = {}
        for sdg_num in range(1, 18):
            sdg = SDG_DEFINITIONS[sdg_num]
            # Combine name, description, and keywords
            text = f"SDG {sdg_num}: {sdg['name']}. Keywords: {', '.join(sdg['keywords'])}"
            embedding = self.model.encode(text, convert_to_numpy=True)
            sdg_embeddings[sdg_num] = embedding
        return sdg_embeddings

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def predict(self, text: str) -> tuple:
        """Predict SDG for text."""
        text_embedding = self.model.encode(text, convert_to_numpy=True)

        # Compute similarity to all SDGs
        scores = {}
        for sdg_num, sdg_emb in self.sdg_embeddings.items():
            sim = self._cosine_similarity(text_embedding, sdg_emb)
            scores[sdg_num] = sim

        # Get top prediction
        top_sdg = max(scores.keys(), key=lambda k: scores[k])
        top_score = scores[top_sdg]

        # Get all scores sorted
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return top_sdg, top_score, sorted_scores


def load_osdg_data(csv_path: Path, min_agreement: float = 0.7, sample_size: int = None) -> pd.DataFrame:
    """Load OSDG data."""
    print(f"Loading OSDG data from {csv_path}...")
    # OSDG data is tab-separated
    try:
        df = pd.read_csv(csv_path, sep='\t', on_bad_lines='skip')
    except TypeError:
        # For older pandas versions
        df = pd.read_csv(csv_path, sep='\t', error_bad_lines=False)
    print(f"Total records: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")

    # Filter by agreement
    df = df[df['agreement'] >= min_agreement].copy()
    print(f"Records with agreement >= {min_agreement}: {len(df)}")

    # Remove empty text
    df = df[df['text'].notna() & (df['text'].str.strip() != '')]
    print(f"Records with valid text: {len(df)}")

    # Sample if needed
    if sample_size and len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)
        print(f"Sampled to {len(df)} records")

    return df


def evaluate(evaluator: SimpleSDGEvaluator, df: pd.DataFrame) -> Dict:
    """Evaluate model against OSDG labels."""

    results = []
    correct = 0

    # Per-SDG metrics
    sdg_stats = defaultdict(lambda: {'correct': 0, 'total': 0})

    print(f"\nEvaluating {len(df)} texts...")

    for idx, row in tqdm(df.iterrows(), total=len(df)):
        text = row['text']
        true_sdg = int(row['sdg'])

        try:
            pred_sdg, pred_score, all_scores = evaluator.predict(text)

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
                'agreement': row['agreement']
            })

        except Exception as e:
            print(f"Error at {idx}: {e}")
            continue

    total = len(results)
    accuracy = correct / total if total > 0 else 0

    # Calculate per-SDG accuracy
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
        'results_df': pd.DataFrame(results)
    }


def analyze_errors(results_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze misclassifications."""
    errors = results_df[results_df['correct'] == False]

    # Count confusion pairs
    confusion = errors.groupby(['true_sdg', 'predicted_sdg']).size().reset_index(name='count')
    confusion = confusion.sort_values('count', ascending=False)

    return confusion.head(10)


def print_report(evaluation: Dict, confusion: pd.DataFrame):
    """Print evaluation report."""

    print("\n" + "="*70)
    print("OSDG EVALUATION REPORT")
    print("="*70)

    print(f"\nOverall Accuracy: {evaluation['accuracy']:.2%}")
    print(f"Correct: {evaluation['correct']} / {evaluation['total']}")

    print("\n" + "-"*70)
    print("PER-SDG ACCURACY")
    print("-"*70)
    print(f"{'SDG':<5} {'Name':<40} {'Accuracy':<10} {'Count':<10}")
    print("-"*70)

    for sdg_num in range(1, 18):
        acc_data = evaluation['sdg_accuracies'][sdg_num]
        if acc_data['total'] > 0:
            name = SDG_DEFINITIONS[sdg_num]['name'][:37]
            print(f"{sdg_num:<5} {name:<40} {acc_data['accuracy']:>8.1%}   {acc_data['correct']:>3}/{acc_data['total']:<3}")

    print("\n" + "-"*70)
    print("TOP MISCLASSIFICATIONS")
    print("-"*70)
    print(f"{'True':<10} → {'Predicted':<10} {'Count':<10}")
    print("-"*70)

    for _, row in confusion.iterrows():
        print(f"SDG {int(row['true_sdg']):<6} → SDG {int(row['predicted_sdg']):<6} {int(row['count'])}")

    print("\n" + "="*70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate SDG model against OSDG")
    parser.add_argument("--model", default="all-mpnet-base-v2")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--sample-size", type=int, default=500)
    parser.add_argument("--min-agreement", type=float, default=0.7)

    args = parser.parse_args()

    # Check for OSDG data
    csv_path = Path("data/external/osdg-community-data-v2024-04-01.csv")
    if not csv_path.exists():
        print(f"OSDG data not found: {csv_path}")
        print("Download: https://zenodo.org/records/11441197")
        return

    # Load data
    df = load_osdg_data(csv_path, args.min_agreement, args.sample_size)

    # Initialize evaluator
    evaluator = SimpleSDGEvaluator(args.model, args.threshold)

    # Run evaluation
    evaluation = evaluate(evaluator, df)

    # Analyze errors
    confusion = analyze_errors(evaluation['results_df'])

    # Print report
    print_report(evaluation, confusion)

    # Save results
    results_csv = Path("data/results/osdg_evaluation_results.csv")
    results_csv.parent.mkdir(parents=True, exist_ok=True)
    evaluation['results_df'].to_csv(results_csv, index=False)
    print(f"\nResults saved to: {results_csv}")


if __name__ == "__main__":
    main()
