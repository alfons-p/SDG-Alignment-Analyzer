#!/usr/bin/env python3
"""Demo script for yearly comparison charts.

This script demonstrates how to use the new yearly comparison visualization
methods to analyze SDG alignment trends across multiple years.

Usage:
    python scripts/demo_yearly_charts.py --results-dir data/results --output-dir data/results/yearly_demo

The script will:
1. Load existing alignment results from JSON files
2. Generate all 6 types of yearly comparison charts
3. Save them to the specified output directory
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports import Reporter


def load_results_from_json(results_dir: Path) -> List[Dict[str, Any]]:
    """Load alignment results from existing JSON files."""
    results = []

    by_council_dir = results_dir / "by_council"
    if not by_council_dir.exists():
        by_council_dir = results_dir

    for json_file in by_council_dir.glob("*_alignment.json"):
        try:
            with open(json_file, 'r') as f:
                result = json.load(f)
                results.append(result)
                print(f"  Loaded: {json_file.name}")
        except Exception as e:
            print(f"  Error loading {json_file}: {e}")

    return results


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Demo yearly comparison charts",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--results-dir", "-r",
        default="data/results",
        help="Directory containing alignment result JSON files"
    )

    parser.add_argument(
        "--output-dir", "-o",
        default="data/results/yearly_demo",
        help="Output directory for charts"
    )

    parser.add_argument(
        "--sort-by",
        choices=["sdg", "coverage"],
        default="sdg",
        help="Sort SDGs by number or by average coverage/score"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Setup paths
    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("YEARLY COMPARISON CHARTS DEMO")
    print("=" * 70)
    print(f"\nResults directory: {results_dir}")
    print(f"Output directory: {output_dir}")

    # Load existing results
    print("\nLoading alignment results...")
    results = load_results_from_json(results_dir)

    if not results:
        print("\nNo results found!")
        print(f"Please run analysis first:")
        print(f"  python scripts/run_analysis.py -i data/raw -o data/results")
        return

    print(f"\nLoaded {len(results)} report(s)")

    # Check for year metadata
    years = set()
    for result in results:
        year = result.get("metadata", {}).get("year", "")
        if year:
            years.add(year)

    if len(years) < 2:
        print(f"\nWarning: Only {len(years)} year(s) found in results.")
        print("Yearly comparison charts work best with data from multiple years.")
        print("Available years:", ", ".join(sorted(years)) if years else "None")

    # Initialize reporter
    reporter = Reporter(output_dir=output_dir)

    # Generate all yearly charts
    print("\n" + "=" * 70)
    print("GENERATING YEARLY COMPARISON CHARTS")
    print("=" * 70)

    # Option 1: Generate all charts at once using comprehensive method
    print("\n[Method 1] Generating comprehensive yearly analysis (all 6 charts)...")
    try:
        all_paths = reporter.create_comprehensive_yearly_analysis(
            results,
            filename_prefix="demo_yearly"
        )
        print(f"\nAll charts saved! Total: {len(all_paths)} files")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    # Option 2: Generate individual chart types
    print("\n" + "=" * 70)
    print("[Method 2] Generating individual chart types...")
    print("=" * 70)

    # 2a. Yearly mean comparison bar chart (similar to comparison_bar.png)
    print("\n1. Yearly Mean Comparison Bar Chart...")
    try:
        path = reporter.create_yearly_mean_comparison_bar_chart(
            results,
            filename="demo_mean_comparison_bar.png",
            sort_by=args.sort_by
        )
        print(f"   Saved: {path.name}")
        print("   Shows mean alignment scores per SDG, grouped by year")
    except Exception as e:
        print(f"   Error: {e}")

    # 2b. Yearly coverage comparison bar chart (similar to coverage_comparison_bar.png)
    print("\n2. Yearly Coverage Comparison Bar Chart...")
    try:
        path = reporter.create_yearly_coverage_comparison_bar_chart(
            results,
            filename="demo_coverage_comparison_bar.png",
            sort_by=args.sort_by
        )
        print(f"   Saved: {path.name}")
        print("   Shows mean coverage % per SDG, grouped by year")
    except Exception as e:
        print(f"   Error: {e}")

    # 2c. Yearly comparison charts (bar + line)
    print("\n3. Yearly Comparison Charts (bar + line)...")
    try:
        paths = reporter.create_yearly_comparison_charts(
            results,
            filename_prefix="demo_comparison"
        )
        print(f"   Bar chart: {paths['bar_chart'].name}")
        print(f"   Line chart: {paths['line_chart'].name}")
    except Exception as e:
        print(f"   Error: {e}")

    # 2d. Yearly coverage comparison charts (bar + line)
    print("\n4. Yearly Coverage Comparison Charts (bar + line)...")
    try:
        paths = reporter.create_yearly_coverage_comparison_charts(
            results,
            filename_prefix="demo_coverage"
        )
        print(f"   Bar chart: {paths['bar_chart'].name}")
        print(f"   Line chart: {paths['line_chart'].name}")
    except Exception as e:
        print(f"   Error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print(f"\nAll charts saved to: {output_dir}")
    print("\nGenerated chart types:")
    print("  1. Yearly Alignment Bar Chart (grouped bars by year)")
    print("  2. Yearly Alignment Line Chart (trends over time)")
    print("  3. Yearly Coverage Bar Chart (grouped bars by year)")
    print("  4. Yearly Coverage Line Chart (trends over time)")
    print("  5. Yearly Mean Comparison Bar Chart (grouped bars by year)")
    print("  6. Yearly Coverage Comparison Bar Chart (grouped bars by year)")
    print("\nChart descriptions:")
    print("  - Bar charts show each SDG with side-by-side bars for each year")
    print("  - Line charts show trends over time for each SDG")


if __name__ == "__main__":
    main()
