#!/usr/bin/env python3
"""Calculate SDG-specific ensemble weights based on benchmark results.

Heuristic: If ST precision > sdgBERT precision by >10%, give ST 65% weight.
Otherwise use default weights (sdgBERT 55%, ST 45%).
"""

import json
from pathlib import Path
from typing import Dict, Tuple


def load_benchmark_data(benchmark_path: Path) -> Dict:
    """Load benchmark results from JSON."""
    with open(benchmark_path) as f:
        return json.load(f)


def extract_precision_values(benchmark_data: list, model_name: str) -> Dict[int, float]:
    """Extract per-SDG precision values from benchmark."""
    for entry in benchmark_data:
        if model_name in entry.get("model", ""):
            sdg_metrics = entry.get("sdg_metrics", {})
            return {
                int(sdg): metrics["precision"]
                for sdg, metrics in sdg_metrics.items()
                if "precision" in metrics
            }
    return {}


def calculate_sdg_weights(
    st_precision: Dict[int, float],
    sdg_bert_precision: Dict[int, float],
    default_st_weight: float = 0.45,
    default_sdg_bert_weight: float = 0.55,
    boosted_st_weight: float = 0.65,
    threshold_diff: float = 0.10
) -> Dict[int, Tuple[float, float]]:
    """
    Calculate SDG-specific ensemble weights.

    Returns dict mapping SDG number to (sdg_bert_weight, st_weight) tuple.
    """
    weights = {}

    for sdg in range(1, 18):
        st_prec = st_precision.get(sdg, 0)
        sdg_bert_prec = sdg_bert_precision.get(sdg, 0)

        # If ST precision is significantly higher, boost ST weight
        if st_prec - sdg_bert_prec > threshold_diff:
            weights[sdg] = (1 - boosted_st_weight, boosted_st_weight)  # (sdg_bert, st)
        else:
            weights[sdg] = (default_sdg_bert_weight, default_st_weight)

    return weights


def print_weight_table(weights: Dict[int, Tuple[float, float]], st_precision: Dict[int, float], sdg_bert_precision: Dict[int, float]):
    """Print a formatted table of SDG weights."""
    print("\n" + "="*80)
    print("SDG-SPECIFIC ENSEMBLE WEIGHTS")
    print("="*80)
    print(f"\n{'SDG':<5} {'ST Precision':<15} {'sdgBERT Prec':<15} {'Diff':<10} {'ST Weight':<12} {'sdgBERT Weight':<15}")
    print("-"*80)

    for sdg in range(1, 18):
        st_prec = st_precision.get(sdg, 0)
        sdg_bert_prec = sdg_bert_precision.get(sdg, 0)
        diff = st_prec - sdg_bert_prec
        sdg_bert_w, st_w = weights[sdg]

        marker = " ***" if st_w > 0.5 else ""
        print(f"{sdg:<5} {st_prec:>13.2%}   {sdg_bert_prec:>13.2%}   {diff:>+8.1%}   {st_w:>10.0%}     {sdg_bert_w:>13.0%}{marker}")

    print("-"*80)
    print("*** = Boosted ST weight (ST precision > sdgBERT by >10%)")
    print("="*80)


def generate_weights_code(weights: Dict[int, Tuple[float, float]]) -> str:
    """Generate Python code for the SDG weights dictionary."""
    lines = [
        "# SDG-specific ensemble weights calculated from benchmark analysis",
        "# Format: {sdg_number: (sdg_bert_weight, st_weight)}",
        "#",
        "# Heuristic: If ST precision > sdgBERT precision by >10%, ST gets 65% weight",
        "# Otherwise: default weights (sdgBERT 55%, ST 45%)",
        "",
        "SDG_ENSEMBLE_WEIGHTS = {",
    ]

    for sdg in range(1, 18):
        sdg_bert_w, st_w = weights[sdg]
        lines.append(f"    {sdg}: ({sdg_bert_w:.2f}, {st_w:.2f}),  # sdgBERT {sdg_bert_w:.0%}, ST {st_w:.0%}")

    lines.append("}")
    lines.append("")
    lines.append("DEFAULT_SDG_BERT_WEIGHT = 0.55")
    lines.append("DEFAULT_ST_WEIGHT = 0.45")

    return "\n".join(lines)


def main():
    """Main function to calculate and display SDG-specific weights."""
    benchmark_path = Path("results/benchmark/benchmark_20260226_161528.json")

    if not benchmark_path.exists():
        print(f"Error: Benchmark file not found at {benchmark_path}")
        return

    # Load benchmark data
    benchmark_data = load_benchmark_data(benchmark_path)

    # Extract precision values for each model
    # Using fine-tuned enhanced model for ST
    st_precision = extract_precision_values(benchmark_data, "sdg-enhanced-finetuned")
    sdg_bert_precision = extract_precision_values(benchmark_data, "sadickam/sdgBERT")

    if not st_precision or not sdg_bert_precision:
        print("Error: Could not extract precision values from benchmark")
        print(f"ST precision found: {bool(st_precision)}")
        print(f"sdgBERT precision found: {bool(sdg_bert_precision)}")
        return

    # Calculate weights
    weights = calculate_sdg_weights(st_precision, sdg_bert_precision)

    # Print results
    print_weight_table(weights, st_precision, sdg_bert_precision)

    # Generate code
    print("\n" + "="*80)
    print("PYTHON CODE FOR SDG WEIGHTS")
    print("="*80)
    print(generate_weights_code(weights))

    # Save to file
    output_path = Path("src/sdg_ensemble_weights.py")
    output_path.write_text(generate_weights_code(weights))
    print(f"\n✓ Weights saved to: {output_path}")


if __name__ == "__main__":
    main()
