#!/usr/bin/env python3
"""Grid search for optimal SDG-specific ensemble weights.

Searches weight space in 5% increments (coarse grid):
- sdgBERT weight: 0.0, 0.05, 0.10, ... 1.0
- ST weight: 1.0, 0.95, 0.90, ... 0.0

Evaluates on OSDG dataset and selects weights that maximize F1 score per SDG.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from tqdm import tqdm
from sklearn.metrics import precision_score, recall_score, f1_score

from src.hybrid_alignment_engine import HybridAlignmentEngine
from src.config import SDG_DEFINITIONS


@dataclass
class WeightConfig:
    """Configuration of weights for a single SDG."""
    sdg: int
    sdg_bert_weight: float
    st_weight: float
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    accuracy: float = 0.0


class GridSearchSDGWeights:
    """Grid search for optimal SDG-specific ensemble weights."""

    def __init__(
        self,
        model_path: str,
        csv_path: Path,
        n_samples_per_sdg: int = 100,
        agreement_threshold: float = 0.7,
        weight_step: float = 0.05
    ):
        self.model_path = model_path
        self.csv_path = csv_path
        self.n_samples_per_sdg = n_samples_per_sdg
        self.agreement_threshold = agreement_threshold
        self.weight_step = weight_step

        # Load OSDG data
        self.osdg_data = self._load_osdg_data()

        # Generate weight combinations (coarse grid)
        self.weight_combinations = self._generate_weight_combinations()

    def _load_osdg_data(self) -> pd.DataFrame:
        """Load and filter OSDG data."""
        print(f"Loading OSDG data from {self.csv_path}...")
        df = pd.read_csv(self.csv_path, sep='\t', on_bad_lines='skip')

        # Filter by agreement threshold
        df = df[df['agreement'] >= self.agreement_threshold].copy()
        df = df[df['text'].notna() & (df['text'].str.strip() != '')]

        print(f"Loaded {len(df)} records with agreement >= {self.agreement_threshold}")
        return df

    def _generate_weight_combinations(self) -> List[Tuple[float, float]]:
        """Generate weight combinations for grid search."""
        combinations = []
        step = self.weight_step

        # sdgBERT weight from 0 to 1 in 5% steps
        # ST weight = 1 - sdgBERT weight
        n_steps = int(1.0 / step) + 1
        for i in range(n_steps):
            sdg_bert_w = round(i * step, 2)
            st_w = round(1.0 - sdg_bert_w, 2)
            combinations.append((sdg_bert_w, st_w))

        print(f"Generated {len(combinations)} weight combinations (step={step})")
        return combinations

    def get_sdg_samples(self, target_sdg: int) -> pd.DataFrame:
        """Get samples for a specific SDG."""
        # Get texts for target SDG
        target_df = self.osdg_data[self.osdg_data['sdg'] == target_sdg].copy()

        # Get texts for other SDGs (negative samples)
        other_df = self.osdg_data[self.osdg_data['sdg'] != target_sdg].copy()

        # Sample to balance
        n_target = min(len(target_df), self.n_samples_per_sdg // 2)
        n_other = self.n_samples_per_sdg - n_target

        if len(target_df) > 0:
            target_df = target_df.sample(n=n_target, random_state=42)
        if len(other_df) > 0:
            other_df = other_df.sample(n=min(n_other, len(other_df)), random_state=42)

        # Combine and create binary labels
        combined = pd.concat([target_df, other_df])
        combined['is_target_sdg'] = (combined['sdg'] == target_sdg).astype(int)

        return combined.sample(frac=1, random_state=42)  # Shuffle

    def evaluate_weights(
        self,
        target_sdg: int,
        sdg_bert_weight: float,
        st_weight: float
    ) -> WeightConfig:
        """Evaluate a specific weight configuration for a target SDG."""
        # Get samples
        samples = self.get_sdg_samples(target_sdg)

        if len(samples) == 0:
            return WeightConfig(
                sdg=target_sdg,
                sdg_bert_weight=sdg_bert_weight,
                st_weight=st_weight
            )

        # Create engine with specific weights
        engine = HybridAlignmentEngine(
            model_name=self.model_path,
            similarity_threshold=0.3,
            use_sdg_bert=True,
            ensemble_mode="weighted",
            sdg_bert_weight=sdg_bert_weight,
            st_weight=st_weight
        )

        # Predict
        predictions = []
        true_labels = []

        for _, row in samples.iterrows():
            text = row['text']
            is_target = row['is_target_sdg']

            try:
                result = engine.align_activity(text, use_ensemble=True)
                pred_is_target = 1 if result['top_sdg'] == target_sdg else 0
                predictions.append(pred_is_target)
                true_labels.append(is_target)
            except Exception as e:
                # Skip on error
                continue

        # Calculate metrics
        if len(predictions) == 0:
            return WeightConfig(
                sdg=target_sdg,
                sdg_bert_weight=sdg_bert_weight,
                st_weight=st_weight
            )

        tp = sum(1 for yt, yp in zip(true_labels, predictions) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(true_labels, predictions) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(true_labels, predictions) if yt == 1 and yp == 0)
        tn = sum(1 for yt, yp in zip(true_labels, predictions) if yt == 0 and yp == 0)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / len(predictions) if len(predictions) > 0 else 0

        return WeightConfig(
            sdg=target_sdg,
            sdg_bert_weight=sdg_bert_weight,
            st_weight=st_weight,
            precision=precision,
            recall=recall,
            f1=f1,
            accuracy=accuracy
        )

    def grid_search_sdg(self, target_sdg: int) -> WeightConfig:
        """Run grid search for optimal weights for a specific SDG."""
        print(f"\n{'='*60}")
        print(f"Grid Search for SDG {target_sdg}")
        print(f"{'='*60}")
        print(f"Testing {len(self.weight_combinations)} weight combinations...")

        results = []
        for sdg_bert_w, st_w in tqdm(self.weight_combinations, desc=f"SDG {target_sdg}"):
            result = self.evaluate_weights(target_sdg, sdg_bert_w, st_w)
            results.append(result)

        # Find best by F1
        best = max(results, key=lambda x: x.f1)

        print(f"\nBest weights for SDG {target_sdg}:")
        print(f"  sdgBERT: {best.sdg_bert_weight:.0%}")
        print(f"  ST:      {best.st_weight:.0%}")
        print(f"  F1:      {best.f1:.2%}")
        print(f"  Precision: {best.precision:.2%}")
        print(f"  Recall:  {best.recall:.2%}")

        return best

    def run_full_grid_search(self, sdgs: Optional[List[int]] = None) -> Dict[int, WeightConfig]:
        """Run grid search for all SDGs."""
        if sdgs is None:
            sdgs = list(range(1, 18))

        print("="*60)
        print("FULL GRID SEARCH FOR SDG-SPECIFIC ENSEMBLE WEIGHTS")
        print("="*60)
        print(f"Weight step size: {self.weight_step}")
        print(f"Weight combinations per SDG: {len(self.weight_combinations)}")
        print(f"SDGs to evaluate: {sdgs}")
        print(f"Total evaluations: {len(self.weight_combinations) * len(sdgs)}")

        results = {}
        for sdg in sdgs:
            best = self.grid_search_sdg(sdg)
            results[sdg] = best

        # Print summary
        print("\n" + "="*60)
        print("GRID SEARCH SUMMARY")
        print("="*60)
        print(f"{'SDG':<5} {'sdgBERT':<10} {'ST':<10} {'F1':<10} {'Notes':<20}")
        print("-"*60)

        for sdg in range(1, 18):
            result = results.get(sdg)
            if result:
                note = ""
                if result.st_weight > 0.5:
                    note = "ST boosted"
                elif result.sdg_bert_weight > 0.6:
                    note = "sdgBERT heavy"
                print(f"{sdg:<5} {result.sdg_bert_weight:<10.0%} {result.st_weight:<10.0%} {result.f1:<10.2%} {note:<20}")

        # Save results
        output_path = Path("results/sdg_grid_search_weights.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        json_results = {
            str(sdg): {
                "sdg_bert_weight": result.sdg_bert_weight,
                "st_weight": result.st_weight,
                "precision": result.precision,
                "recall": result.recall,
                "f1": result.f1,
                "accuracy": result.accuracy
            }
            for sdg, result in results.items()
        }

        with open(output_path, 'w') as f:
            json.dump(json_results, f, indent=2)

        print(f"\n✓ Results saved to: {output_path}")

        return results


def main():
    """Main entry point for grid search."""
    import argparse

    parser = argparse.ArgumentParser(description="Grid search for SDG-specific ensemble weights")
    parser.add_argument("--model-path", default="models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509",
                        help="Path to fine-tuned model")
    parser.add_argument("--csv-path", default="data/external/osdg-community-data-v2024-04-01.csv",
                        help="Path to OSDG data")
    parser.add_argument("--sdgs", nargs="+", type=int, default=None,
                        help="Specific SDGs to evaluate (default: all)")
    parser.add_argument("--n-samples", type=int, default=100,
                        help="Samples per SDG for evaluation")
    parser.add_argument("--weight-step", type=float, default=0.05,
                        help="Weight step size (default: 0.05 = 5%)")

    args = parser.parse_args()

    # Create grid searcher
    searcher = GridSearchSDGWeights(
        model_path=args.model_path,
        csv_path=Path(args.csv_path),
        n_samples_per_sdg=args.n_samples,
        weight_step=args.weight_step
    )

    # Run grid search
    results = searcher.run_full_grid_search(sdgs=args.sdgs)

    # Generate Python code for optimal weights
    print("\n" + "="*60)
    print("GENERATED WEIGHTS CONFIGURATION")
    print("="*60)
    print("\n# Add this to src/sdg_ensemble_weights.py:")
    print("\nGRID_SEARCH_WEIGHTS = {")
    for sdg in range(1, 18):
        result = results.get(sdg)
        if result:
            print(f"    {sdg}: ({result.sdg_bert_weight:.2f}, {result.st_weight:.2f}),  # F1={result.f1:.2%}")
    print("}")


if __name__ == "__main__":
    main()
