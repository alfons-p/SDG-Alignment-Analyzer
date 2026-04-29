#!/usr/bin/env python3
"""Test SDG-specific ensemble weights implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT


def test_sdg_weights():
    """Test that SDG-specific weights are correctly defined."""
    print("="*60)
    print("Testing SDG-Specific Ensemble Weights")
    print("="*60)

    # Check all SDGs are defined
    for sdg in range(1, 18):
        assert sdg in SDG_ENSEMBLE_WEIGHTS, f"SDG {sdg} not in weights dict"
        sdg_bert_w, st_w = SDG_ENSEMBLE_WEIGHTS[sdg]
        assert abs(sdg_bert_w + st_w - 1.0) < 0.001, f"Weights for SDG {sdg} don't sum to 1.0"

    print("✓ All 17 SDGs have valid weights (sum to 1.0)")

    # Check SDG 12 has boosted ST weight
    sdg_12_bert_w, sdg_12_st_w = SDG_ENSEMBLE_WEIGHTS[12]
    assert sdg_12_st_w > 0.5, "SDG 12 should have ST weight > 50%"
    assert sdg_12_st_w == 0.65, "SDG 12 ST weight should be 65%"
    print(f"✓ SDG 12 has boosted ST weight: {sdg_12_st_w:.0%} (sdgBERT: {sdg_12_bert_w:.0%})")

    # Count how many SDGs have non-default weights
    non_default = []
    for sdg in range(1, 18):
        weights = SDG_ENSEMBLE_WEIGHTS[sdg]
        if weights != (DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT):
            non_default.append(sdg)

    print(f"✓ SDGs with non-default weights: {non_default}")

    # Print summary table
    print("\n" + "-"*60)
    print("SDG Weights Summary:")
    print("-"*60)
    for sdg in range(1, 18):
        sdg_bert_w, st_w = SDG_ENSEMBLE_WEIGHTS[sdg]
        marker = " ***" if st_w > 0.5 else ""
        print(f"  SDG {sdg:2d}: ST={st_w:.0%}, sdgBERT={sdg_bert_w:.0%}{marker}")

    print("\n*** = Boosted ST weight")
    print("="*60)
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    test_sdg_weights()
