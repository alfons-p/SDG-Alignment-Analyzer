"""Threshold configuration for SDG alignment optimization.
Auto-generated from results/threshold_optimization_full.json (2026-04-20T14:46:42.818640).
FP ceiling: 0.35 | Date: 2026-04-20
"""
from typing import Dict, Optional

THRESHOLD_CONFIG = {
    "date": "2026-04-20",
    "description": "Auto-generated from results/threshold_optimization_full.json",

    "sentence_transformer": {
        "default": 0.52,
        "sdg_specific": {
        1: 0.653,
        2: 0.564,
        3: 0.610,
        4: 0.484,
        5: 0.631,
        6: 0.628,
        7: 0.585,
        8: 0.443,
        9: 0.459,
        10: 0.639,
        11: 0.158,
        12: 0.615,
        13: 0.542,
        14: 0.602,
        15: 0.641,
        16: 0.610,
        17: 0.036,
        }
    },

    "sdgbert": {
        "default": 0.8,
        "sdg_specific": {
        1: 0.862,
        2: 0.890,
        3: 0.800,
        4: 0.790,
        5: 0.770,
        6: 0.916,
        7: 0.830,
        8: 0.710,
        9: 0.630,
        10: 0.810,
        11: 0.733,
        12: 0.860,
        13: 0.768,
        14: 0.948,
        15: 0.944,
        16: 0.790,
        17: 0.550,
        }
    },

    "hybrid": {
        "default": 0.75,
        "sdg_specific": {
        1: 0.928,
        2: 0.820,
        3: 0.840,
        4: 0.740,
        5: 0.830,
        6: 0.945,
        7: 0.860,
        8: 0.730,
        9: 0.691,
        10: 0.748,
        11: 0.459,
        12: 0.738,
        13: 0.765,
        14: 0.973,
        15: 0.869,
        16: 0.740,
        17: 0.059,
        }
    },
}

def get_threshold(mode: str, sdg: Optional[int] = None) -> float:
    """Get threshold for specified mode and SDG."""
    mode = mode.lower()
    if mode == 'st':
        mode = 'sentence_transformer'
    elif mode == 'bert':
        mode = 'sdgbert'
    if mode not in THRESHOLD_CONFIG:
        raise ValueError(f'Unknown mode: {mode}')
    config = THRESHOLD_CONFIG[mode]
    if sdg is not None and sdg in config.get('sdg_specific', {}):
        return config['sdg_specific'][sdg]
    return config['default']

def get_all_thresholds(mode: str) -> Dict[int, float]:
    """Get all SDG-specific thresholds for a mode."""
    mode = mode.lower()
    if mode == 'st':
        mode = 'sentence_transformer'
    elif mode == 'bert':
        mode = 'sdgbert'
    if mode not in THRESHOLD_CONFIG:
        raise ValueError(f'Unknown mode: {mode}')
    config = THRESHOLD_CONFIG[mode]
    return {
        sdg: config.get('sdg_specific', {}).get(sdg, config['default'])
        for sdg in range(1, 18)
    }

if __name__ == "__main__":
    import json as _json
    print(_json.dumps({k: get_all_thresholds(k) for k in ['st', 'sdgbert', 'hybrid']}, indent=2))
