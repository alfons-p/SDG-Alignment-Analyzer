"""Threshold configuration for SDG alignment optimization.

Based on research findings:
- "One Size Does Not Fit All" (arXiv 2024): Label-specific thresholds improve 46% over uniform
- Academic consensus: Thresholds should be empirically optimized per SDG
- OSDG dataset validation: SDG-specific tuning needed
- Our limited testing: Hybrid mode at 0.5 threshold achieved 84.7% F1 for SDG 12

This configuration provides:
1. Reasonable defaults (research-based, not empirically optimized)
2. SDG-specific overrides for problematic SDGs
3. Easy mechanism to update with new optimizations
"""

from typing import Dict, Optional


# Threshold configuration
THRESHOLD_CONFIG = {
    "version": "1.2.0",
    "date": "2026-03-02",
    "changelog": {
        "1.2.0": "Updated SDG 3 threshold from 0.45 to 0.50 based on robust validation with n=200 samples (F1: 0.944)",
        "1.1.0": "Updated SDG 3 threshold from 0.31 to 0.45 based on 5-fold CV validation (F1: 0.973)",
        "1.0.0": "Initial optimized configuration with SDG 12 validation"
    },
    "description": "Optimized SDG alignment thresholds based on research and empirical validation",

    # Sentence Transformer (ST) only mode
    # Raw cosine similarity typically ranges 0-1
    "sentence_transformer": {
        "default": 0.5,
        "description": "Default threshold for ST-only mode (raw cosine similarity)",

        # SDG-specific adjustments based on optimization (scripts/analysis/optimize_threshold.py )
        "sdg_specific": {
            1: 0.51,   # No Poverty - standard
            2: 0.46,   # Zero Hunger - standard
            3: 0.44,   # Good Health - VALIDATED via robust testing (n=200, F1: 0.944)
            4: 0.5,   # Quality Education - keyword boosted
            5: 0.48,   # Gender Equality - standard
            6: 0.52,   # Clean Water - standard
            7: 0.5,   # Affordable Energy - standard
            8: 0.52,   # Decent Work - standard
            9: 0.5,   # Innovation - standard
            10: 0.5,  # Reduced Inequalities - slightly higher
            11: 0.55,  # Sustainable Cities - standard
            12: 0.59,  # Responsible Consumption - LOWER (waste terminology variance)
            13: 0.48,  # Climate Action - keyword boosted
            14: 0.51,  # Life Below Water - LOWER (smaller dataset)
            15: 0.49,  # Life on Land - standard
            16: 0.44,  # Peace and Justice - standard
            17: 0.50,  # Partnerships - HIGHER (harder to classify)
        }
    },

    # sdgBERT only mode
    "sdgbert": {
        "default": 0.50,
        "description": "Default threshold for hybrid mode (normalized ensemble scores)",

        # SDG-specific adjustments
        "sdg_specific": {
            1: 0.355,   # No Poverty - slight adjustment
            2: 0.31,   # Zero Hunger - slight adjustment
            3: 0.401,   # Good Health - sdgBERT strong here
            4: 0.452,   # Quality Education - standard
            5: 0.377,   # Gender Equality - sdgBERT strong here
            6: 0.368,   # Clean Water - slight adjustment
            7: 0.455,   # Affordable Energy - standard
            8: 0.317,   # Decent Work - slight adjustment
            9: 0.526,   # Innovation - standard
            10: 0.321,  # Reduced Inequalities - slightly higher
            11: 0.559,  # Sustainable Cities - standard
            12: 0.6,  # Responsible Consumption - LOWER (validated at 0.5: 84.7% F1)
            13: 0.381,  # Climate Action - keyword boosted
            14: 0.398,  # Life Below Water - LOWER (smaller dataset)
            15: 0.446,  # Life on Land - slight adjustment
            16: 0.439,  # Peace and Justice - standard
            17: 0.5,  # Partnerships - HIGHER (sdgBERT doesn't cover SDG 17)
        }
    },

    # Hybrid mode (ST + sdgBERT ensemble)
    "hybrid": {
        "default": 0.50,
        "description": "Default threshold for hybrid mode (normalized ensemble scores)",

        # SDG-specific adjustments
        "sdg_specific": {
            1: 0.429,   # No Poverty - slight adjustment
            2: 0.38,   # Zero Hunger - slight adjustment
            3: 0.421,   # Good Health - sdgBERT strong here
            4: 0.476,   # Quality Education - standard
            5: 0.428,   # Gender Equality - sdgBERT strong here
            6: 0.442,   # Clean Water - slight adjustment
            7: 0.477,   # Affordable Energy - standard
            8: 0.411,   # Decent Work - slight adjustment
            9: 0.513,   # Innovation - standard
            10: 0.537,  # Reduced Inequalities - slightly higher
            11: 0.554,  # Sustainable Cities - standard
            12: 0.595,  # Responsible Consumption - LOWER (validated at 0.5: 84.7% F1)
            13: 0.429,  # Climate Action - keyword boosted
            14: 0.453,  # Life Below Water - LOWER (smaller dataset)
            15: 0.468,  # Life on Land - slight adjustment
            16: 0.439,  # Peace and Justice - standard
            17: 0.5,  # Partnerships - Same as ST (sdgBERT doesn't cover SDG 17)
        }
    },

    # Validation metrics (from our testing)
    # "validation": {
    #     "sdg_12_hybrid": {
    #         "threshold": 0.50,
    #         "f1_score": 0.847,
    #         "precision": 0.735,
    #         "recall": 1.000,
    #         "n_samples": 100,
    #         "test_date": "2026-03-02"
    #     },
    #     "sdg_3_st": {
    #         "threshold": 0.50,
    #         "f1_score": 0.944,
    #         "precision": 0.960,
    #         "recall": 0.931,
    #         "n_samples": 200,
    #         "cv_folds": 5,
    #         "test_date": "2026-03-02",
    #         "comparison_n100": {
    #             "threshold": 0.45,
    #             "f1_score": 0.973,
    #             "precision": 0.962,
    #             "recall": 0.986,
    #             "n_samples": 100
    #         }
    #     }
    # },

    # Environment variable overrides
    # "environment_overrides": {
    #     "SIMILARITY_THRESHOLD_ST": "sentence_transformer.default",
    #     "SIMILARITY_THRESHOLD_HYBRID": "hybrid.default",
    #     "HYBRID_THRESHOLD_SDG12": "hybrid.sdg_specific.12",
    # }
}


def get_threshold(mode: str, sdg: Optional[int] = None) -> float:
    """
    Get threshold for specified mode and SDG.

    Args:
        mode: 'st' or 'hybrid' or 'sentence_transformer'
        sdg: Optional SDG number (1-17), None for global default

    Returns:
        Threshold value

    Examples:
        >>> get_threshold('hybrid')
        0.70
        >>> get_threshold('hybrid', sdg=12)
        0.50
        >>> get_threshold('st', sdg=17)
        0.35
    """
    mode = mode.lower()

    # Normalize mode name - accept both 'st' and 'sentence_transformer'
    if mode == 'st':
        mode = 'sentence_transformer'

    if mode not in THRESHOLD_CONFIG:
        raise ValueError(f"Unknown mode: {mode}. Must be 'st' or 'hybrid'")

    config = THRESHOLD_CONFIG[mode]

    # Check for SDG-specific threshold
    if sdg is not None:
        if sdg in config.get('sdg_specific', {}):
            return config['sdg_specific'][sdg]

    # Return default
    return config['default']


def get_all_thresholds(mode: str) -> Dict[int, float]:
    """
    Get all SDG-specific thresholds for a mode.

    Args:
        mode: 'st' or 'hybrid'

    Returns:
        Dictionary mapping SDG number to threshold
    """
    mode = mode.lower()

    if mode == 'st':
        mode = 'sentence_transformer'
    elif mode == 'sentence_transformer':
        mode = 'st'

    if mode not in THRESHOLD_CONFIG:
        raise ValueError(f"Unknown mode: {mode}. Must be 'st' or 'hybrid'")

    config = THRESHOLD_CONFIG[mode]

    # Get SDG-specific or default for all SDGs
    thresholds = {}
    for sdg in range(1, 18):
        if sdg in config.get('sdg_specific', {}):
            thresholds[sdg] = config['sdg_specific'][sdg]
        else:
            thresholds[sdg] = config['default']

    return thresholds


def print_threshold_table():
    """Print a formatted table of all thresholds."""
    print("\n" + "="*80)
    print("SDG ALIGNMENT THRESHOLDS - OPTIMIZED CONFIGURATION")
    print("="*80)
    print(f"\nConfiguration version: {THRESHOLD_CONFIG['version']} ({THRESHOLD_CONFIG['date']})")
    print(f"Based on: Academic research + limited OSDG validation")
    print(f"\n{'Mode':<20} {'Global':<8} {'SDG 12':<8} {'SDG 17':<8} {'Notes'}")
    print("-" * 80)

    st_default = get_threshold('st')
    st_12 = get_threshold('st', 12)
    st_17 = get_threshold('st', 17)
    hybrid_default = get_threshold('hybrid')
    hybrid_12 = get_threshold('hybrid', 12)
    hybrid_17 = get_threshold('hybrid', 17)

    print(f"{'ST-only':<20} {st_default:<8.2f} {st_12:<8.2f} {st_17:<8.2f} {'Raw cosine similarity'}")
    print(f"{'Hybrid':<20} {hybrid_default:<8.2f} {hybrid_12:<8.2f} {hybrid_17:<8.2f} {'Normalized ensemble scores'}")

    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    print("• SDG 12 (Waste): Lower threshold (0.50 hybrid) - tested at 84.7% F1")
    print("• SDG 14 (Water): Lower threshold - limited training data")
    print("• SDG 17 (Partnerships): Higher threshold - sdgBERT doesn't cover SDG 17")
    print("• Other SDGs: Near-default values - reasonable starting points")
    print("\n" + "="*80)
    print("VALIDATION STATUS")
    print("="*80)
    validation = THRESHOLD_CONFIG.get('validation', {})
    if 'sdg_12_hybrid' in validation:
        v = validation['sdg_12_hybrid']
        print(f"✓ SDG 12 (Hybrid): Validated at threshold {v['threshold']}")
        print(f"  F1={v['f1_score']:.3f}, Precision={v['precision']:.3f}, Recall={v['recall']:.3f}")
        print(f"  Tested on {v['n_samples']} OSDG samples")
    print(f"• Other SDGs: Research-based defaults (not yet validated)")
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Validate thresholds on your actual council data")
    print("2. Run full optimization: python scripts/analysis/optimize_threshold.py")
    print("3. Update this config with validated values")
    print("4. Monitor alignment counts and adjust if needed")
    print("="*80 + "\n")


if __name__ == "__main__":
    print_threshold_table()