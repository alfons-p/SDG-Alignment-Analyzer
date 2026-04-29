#!/usr/bin/env python3
"""Example script demonstrating the alignment summary features.

This script shows how to:
1. Load existing alignment results
2. Create alignment_summary.csv with coverage for all SDGs
3. Create coverage_comparison_chart.png
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports import Reporter


def load_results_from_json(results_dir: Path) -> List[Dict[str, Any]]:
    """Load alignment results from existing JSON files."""
    results = []

    for json_file in results_dir.glob("*_alignment.json"):
        try:
            with open(json_file, 'r') as f:
                result = json.load(f)
                results.append(result)
                print(f"Loaded: {json_file.name}")
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return results


def main():
    """Generate alignment summary and coverage chart."""
    # Setup
    results_dir = Path("data/results")
    output_dir = Path("data/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SDG Alignment Summary Generator")
    print("=" * 70)

    # Initialize reporter
    reporter = Reporter(output_dir=output_dir)

    # Load existing results
    print("\nLoading existing alignment results...")
    results = load_results_from_json(results_dir)

    if not results:
        print("No results found in data/results/*.json")
        print("Please run the analysis first:")
        print("  python scripts/run_analysis.py --input data/raw/ --output data/results/ --compare")
        return

    print(f"\nLoaded {len(results)} report(s)")

    # Create alignment summary
    print("\n" + "=" * 70)
    print("Creating Alignment Summary (All SDGs Coverage)")
    print("=" * 70)

    try:
        # Create DataFrame
        alignment_df = reporter.create_alignment_summary(results)

        # Save to CSV
        alignment_csv = output_dir / "alignment_summary.csv"
        alignment_df.to_csv(alignment_csv, index=False)
        print(f"\nSaved: {alignment_csv}")

        # Display preview
        print("\nPreview (first 5 columns):")
        preview_cols = ['source', 'total_activities'] + [f'sdg_{i}_coverage' for i in range(1, 6)]
        print(alignment_df[preview_cols].to_string(index=False))

        # Show full SDG coverage for first council
        if len(alignment_df) > 0:
            print(f"\nFull SDG Coverage for {alignment_df.iloc[0]['source']}:")
            for i in range(1, 18):
                coverage = alignment_df.iloc[0][f'sdg_{i}_coverage'] * 100
                sdg_name = alignment_df.iloc[0][f'sdg_{i}_name']
                print(f"  SDG {i}: {coverage:.1f}% - {sdg_name}")

    except Exception as e:
        print(f"Error creating alignment summary: {e}")
        import traceback
        traceback.print_exc()

    # Create coverage comparison chart
    print("\n" + "=" * 70)
    print("Creating Coverage Comparison Chart")
    print("=" * 70)

    try:
        coverage_chart_path = reporter.create_coverage_comparison_chart(
            results,
            filename="coverage_comparison_chart.png",
            sort_by="sdg"  # Sort by SDG number (SDG 1, 2, 3... 17)
        )
        print(f"\nSaved: {coverage_chart_path}")
        print("\nThis chart shows the proportion of activities where is_aligned=True")
        print("for EACH of the 17 SDGs, grouped by council.")
        print("SDGs are sorted by number (SDG 1 → SDG 17).")

    except Exception as e:
        print(f"Error creating coverage chart: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)
    print(f"\nFiles created:")
    print(f"  - {output_dir / 'alignment_summary.csv'}")
    print(f"  - {output_dir / 'coverage_comparison_chart.png'}")


if __name__ == "__main__":
    main()
