#!/usr/bin/env python3
"""Minimal test of grid search logic without model loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_weight_combinations():
    """Test weight combination generation."""
    weight_step = 0.05
    combinations = []
    n_steps = int(1.0 / weight_step) + 1

    for i in range(n_steps):
        sdg_bert_w = round(i * weight_step, 2)
        st_w = round(1.0 - sdg_bert_w, 2)
        combinations.append((sdg_bert_w, st_w))

    print("="*60)
    print("Weight Combinations (5% steps)")
    print("="*60)
    print(f"Total combinations: {len(combinations)}")
    print("\nFirst 10:")
    for i, (bert_w, st_w) in enumerate(combinations[:10]):
        print(f"  {i+1:2d}. sdgBERT={bert_w:.0%}, ST={st_w:.0%}")
    print("\nLast 10:")
    for i, (bert_w, st_w) in enumerate(combinations[-10:], len(combinations)-10):
        print(f"  {i+1:2d}. sdgBERT={bert_w:.0%}, ST={st_w:.0%}")

    # Verify all combinations sum to 1.0
    for bert_w, st_w in combinations:
        assert abs(bert_w + st_w - 1.0) < 0.001, f"Weights don't sum to 1.0: {bert_w} + {st_w}"

    print("\n✓ All weight combinations sum to 1.0")
    print("="*60)


def test_sdg_specific_weights():
    """Test that SDG-specific weights are correctly defined."""
    from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT

    print("\n" + "="*60)
    print("SDG-Specific Weights Test")
    print("="*60)

    # Check all SDGs are defined
    for sdg in range(1, 18):
        assert sdg in SDG_ENSEMBLE_WEIGHTS, f"SDG {sdg} not in weights dict"
        sdg_bert_w, st_w = SDG_ENSEMBLE_WEIGHTS[sdg]
        assert abs(sdg_bert_w + st_w - 1.0) < 0.001, f"Weights for SDG {sdg} don't sum to 1.0"

    print("✓ All 17 SDGs have valid weights (sum to 1.0)")

    # Count non-default weights
    non_default = []
    for sdg in range(1, 18):
        weights = SDG_ENSEMBLE_WEIGHTS[sdg]
        if weights != (DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT):
            non_default.append((sdg, weights))

    print(f"✓ SDGs with non-default weights: {len(non_default)}")
    for sdg, (bert_w, st_w) in non_default:
        print(f"  - SDG {sdg}: ST={st_w:.0%}, sdgBERT={bert_w:.0%}")

    print("="*60)


if __name__ == "__main__":
    test_weight_combinations()
    test_sdg_specific_weights()
    print("\n✓ All tests passed!")
