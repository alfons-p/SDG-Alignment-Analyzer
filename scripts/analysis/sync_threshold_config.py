#!/usr/bin/env python3
"""Sync optimized thresholds from JSON results into Python config files.

Reads results/threshold_optimization_full.json and regenerates:
  - src/config/threshold_config.py
  - src/sdg_ensemble_weights.py

Usage:
    python scripts/analysis/sync_threshold_config.py --dry-run
    python scripts/analysis/sync_threshold_config.py
"""

import sys
from pathlib import Path
import json
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DEFAULT_JSON_PATH = Path("results/threshold_optimization_full.json")


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"Error: {path} not found. Run optimize_thresholds.py first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def compute_ensemble_weights(data: dict) -> dict:
    """Compute per-SDG weights: w = precision / (st_precision + sdgbert_precision)."""
    st_per = data.get("st", {}).get("per_sdg", {})
    bert_per = data.get("sdgbert", {}).get("per_sdg", {})
    weights = {}
    for sdg in range(1, 18):
        st_p = st_per.get(str(sdg), {}).get("precision", 0)
        bert_p = bert_per.get(str(sdg), {}).get("precision", 0)
        total = st_p + bert_p
        if total > 0:
            st_w = round(st_p / total, 3)
            bert_w = round(1.0 - st_w, 3)
        else:
            st_w, bert_w = 0.50, 0.50
        weights[sdg] = (bert_w, st_w)
    return weights


def generate_threshold_config(data: dict) -> str:
    ts = data.get("timestamp", "")
    date_str = ts.split("T")[0] if ts else ""
    fp_ceiling = data.get("fp_ceiling", 0.35)

    mode_map = [("st", "sentence_transformer"), ("sdgbert", "sdgbert"), ("hybrid", "hybrid")]

    sections = []
    for key, config_key in mode_map:
        if key not in data:
            continue
        section = data[key]
        thresholds = {int(k): float(v) for k, v in section.get("thresholds", {}).items()}
        default_val = round(sum(thresholds.values()) / len(thresholds), 2) if thresholds else 0.5
        sections.append((config_key, default_val, thresholds))

    # Build the Python source
    parts = []
    parts.append('"""Threshold configuration for SDG alignment optimization.')
    parts.append(f"\nAuto-generated from results/threshold_optimization_full.json ({ts}).")
    parts.append(f"\nFP ceiling: {fp_ceiling} | Date: {date_str}\n\"\"\"")
    parts.append("\nfrom typing import Dict, Optional\n\n")
    parts.append("THRESHOLD_CONFIG = {\n")
    parts.append(f'    "date": "{date_str}",\n')
    parts.append('    "description": "Auto-generated from results/threshold_optimization_full.json",\n')

    for idx, (config_key, default_val, thresholds) in enumerate(sections):
        parts.append(f'\n    "{config_key}": {{\n')
        parts.append(f'        "default": {default_val},\n')
        parts.append(f'        "sdg_specific": {{\n')
        for sdg_num in sorted(thresholds):
            t = thresholds[sdg_num]
            parts.append(f"        {sdg_num}: {t:.3f},\n")
        parts.append("        }\n")
        parts.append("    },\n")

    parts.append("}\n\n")

    # Accessor functions
    parts.append('def get_threshold(mode: str, sdg: Optional[int] = None) -> float:\n')
    parts.append('    """Get threshold for specified mode and SDG."""\n')
    parts.append("    mode = mode.lower()\n")
    parts.append("    if mode == 'st':\n")
    parts.append("        mode = 'sentence_transformer'\n")
    parts.append("    elif mode == 'bert':\n")
    parts.append("        mode = 'sdgbert'\n")
    parts.append("    if mode not in THRESHOLD_CONFIG:\n")
    parts.append("        raise ValueError(f'Unknown mode: {mode}')\n")
    parts.append("    config = THRESHOLD_CONFIG[mode]\n")
    parts.append("    if sdg is not None and sdg in config.get('sdg_specific', {}):\n")
    parts.append("        return config['sdg_specific'][sdg]\n")
    parts.append("    return config['default']\n\n")

    parts.append("def get_all_thresholds(mode: str) -> Dict[int, float]:\n")
    parts.append('    """Get all SDG-specific thresholds for a mode."""\n')
    parts.append("    mode = mode.lower()\n")
    parts.append("    if mode == 'st':\n")
    parts.append("        mode = 'sentence_transformer'\n")
    parts.append("    elif mode == 'bert':\n")
    parts.append("        mode = 'sdgbert'\n")
    parts.append("    if mode not in THRESHOLD_CONFIG:\n")
    parts.append("        raise ValueError(f'Unknown mode: {mode}')\n")
    parts.append("    config = THRESHOLD_CONFIG[mode]\n")
    parts.append("    return {\n")
    parts.append("        sdg: config.get('sdg_specific', {}).get(sdg, config['default'])\n")
    parts.append("        for sdg in range(1, 18)\n")
    parts.append("    }\n\n")

    parts.append('if __name__ == "__main__":\n')
    parts.append("    import json as _json\n")
    parts.append("    print(_json.dumps({k: get_all_thresholds(k) for k in ['st', 'sdgbert', 'hybrid']}, indent=2))\n")

    return "".join(parts)


def generate_ensemble_weights(weights: dict) -> str:
    lines = [f"    {sdg}: ({weights[sdg][0]}, {weights[sdg][1]})," for sdg in range(1, 18)]
    return (
        "# SDG-specific ensemble weights\n"
        "# Auto-generated by scripts/analysis/sync_threshold_config.py\n"
        "# Format: {sdg_number: (sdg_bert_weight, st_weight)}\n"
        "# weight = precision / (st_precision + sdgbert_precision)\n\n"
        "SDG_ENSEMBLE_WEIGHTS = {\n"
        + "\n".join(lines)
        + "\n}\n\n"
        "DEFAULT_SDG_BERT_WEIGHT = 0.50\n"
        "DEFAULT_ST_WEIGHT = 0.50\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Sync thresholds from JSON into Python config")
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = load_json(args.json_path)
    weights = compute_ensemble_weights(data)

    threshold_content = generate_threshold_config(data)
    weights_content = generate_ensemble_weights(weights)

    if args.dry_run:
        print("--- src/config/threshold_config.py ---\n")
        print(threshold_content)
        print("\n--- src/sdg_ensemble_weights.py ---\n")
        print(weights_content)
        return

    p1 = Path("src/config/threshold_config.py")
    p2 = Path("src/sdg_ensemble_weights.py")

    with open(p1, "w") as f:
        f.write(threshold_content)
    print(f"Wrote {p1}")

    with open(p2, "w") as f:
        f.write(weights_content)
    print(f"Wrote {p2}")

    print("\nWeights:")
    for sdg in range(1, 18):
        b, s = weights[sdg]
        print(f"  SDG {sdg:2d}: sdgBERT={b:.3f}, ST={s:.3f}")


if __name__ == "__main__":
    main()
