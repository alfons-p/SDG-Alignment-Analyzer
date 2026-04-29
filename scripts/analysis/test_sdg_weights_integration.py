#!/usr/bin/env python3
"""Quick integration test for SDG-specific ensemble weights."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hybrid_alignment_engine import HybridAlignmentEngine
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS


def test_sdg_weights_integration():
    """Test that HybridAlignmentEngine uses SDG-specific weights."""
    print("="*60)
    print("Testing HybridAlignmentEngine SDG-Specific Weights")
    print("="*60)

    # Create a mock engine to test the _get_sdg_weights method
    engine = HybridAlignmentEngine.__new__(HybridAlignmentEngine)

    # Test that SDG 12 has boosted ST weight
    sdg_12_weights = engine._get_sdg_weights(12)
    assert sdg_12_weights == (0.35, 0.65), f"SDG 12 weights should be (0.35, 0.65), got {sdg_12_weights}"
    print(f"✓ SDG 12 weights: sdgBERT={sdg_12_weights[0]:.0%}, ST={sdg_12_weights[1]:.0%}")

    # Test that other SDGs use default weights
    sdg_1_weights = engine._get_sdg_weights(1)
    assert sdg_1_weights == (0.55, 0.45), f"SDG 1 weights should be (0.55, 0.45), got {sdg_1_weights}"
    print(f"✓ SDG 1 weights: sdgBERT={sdg_1_weights[0]:.0%}, ST={sdg_1_weights[1]:.0%} (default)")

    sdg_5_weights = engine._get_sdg_weights(5)
    assert sdg_5_weights == (0.55, 0.45), f"SDG 5 weights should be (0.55, 0.45), got {sdg_5_weights}"
    print(f"✓ SDG 5 weights: sdgBERT={sdg_5_weights[0]:.0%}, ST={sdg_5_weights[1]:.0%} (default)")

    # Test that unknown SDG falls back to default
    sdg_99_weights = engine._get_sdg_weights(99)
    assert sdg_99_weights == (0.55, 0.45), f"Unknown SDG should use default weights"
    print(f"✓ Unknown SDG (99) falls back to default: sdgBERT={sdg_99_weights[0]:.0%}, ST={sdg_99_weights[1]:.0%}")

    print("\n" + "="*60)
    print("All integration tests passed!")
    print("="*60)


if __name__ == "__main__":
    test_sdg_weights_integration()
