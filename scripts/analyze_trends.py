#!/usr/bin/env python3
"""CLI script for SDG trend analysis.

Analyzes trends in SDG alignment over time across councils, states, and years.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Environment variables are loaded centrally by EnvLoader
# No need to call load_dotenv here - EnvLoader auto-loads on import
from src.config.env_loader import EnvLoader

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trends import TrendAnalyzer


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze SDG alignment trends over time",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--results-dir", "-r",
        default="results",
        help="Directory containing analysis results"
    )

    parser.add_argument(
        "--output", "-o",
        default="results/trends",
        help="Output directory for trend analysis results"
    )

    parser.add_argument(
        "--council",
        help="Analyze trends for a specific council"
    )

    parser.add_argument(
        "--state",
        choices=["NSW", "VIC"],
        help="Analyze trends for a specific state"
    )

    parser.add_argument(
        "--sdg",
        type=int,
        choices=range(1, 18),
        metavar="SDG",
        help="Focus on a specific SDG (1-17)"
    )

    parser.add_argument(
        "--list-councils",
        action="store_true",
        help="List available councils and exit"
    )

    parser.add_argument(
        "--viz-only",
        action="store_true",
        help="Only generate visualizations (skip text report)"
    )

    parser.add_argument(
        "--format",
        choices=["all", "csv", "json", "txt"],
        default="all",
        help="Output format"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    print("SDG Trend Analyzer")
    print("=" * 60)

    # Initialize trend analyzer
    results_dir = Path(args.results_dir)
    trend_analyzer = TrendAnalyzer(results_dir=results_dir)

    # List councils if requested
    if args.list_councils:
        print("\nAvailable Councils:")
        print("-" * 60)

        all_results = trend_analyzer.load_council_results()
        councils = {}

        for result in all_results:
            source = result.get('source', '')
            council_name = source.split('/')[-1].replace('.pdf', '').replace('_', ' ')
            year = result.get('metadata', {}).get('year', 'Unknown')
            state = result.get('metadata', {}).get('state', 'Unknown')

            if council_name not in councils:
                councils[council_name] = {'years': set(), 'state': state}
            councils[council_name]['years'].add(year)

        for council_name in sorted(councils.keys()):
            info = councils[council_name]
            years_str = ', '.join(sorted(info['years']))
            print(f"  {council_name} ({info['state']}): {years_str}")

        print(f"\nTotal: {len(councils)} councils")
        return

    # Determine analysis scope
    if args.council:
        print(f"\nAnalyzing trends for council: {args.council}")
        trends = trend_analyzer.analyze_council_trends(args.council)
        title = f"SDG Trends for {args.council}"
    elif args.state:
        print(f"\nAnalyzing trends for state: {args.state}")
        trends = trend_analyzer.analyze_state_trends(args.state)
        title = f"SDG Trends for {args.state}"
    else:
        print("\nAnalyzing overall trends across all councils")
        trends = trend_analyzer.analyze_overall_trends()
        title = "Overall SDG Trends"

    if not trends:
        print("\nError: Insufficient data for trend analysis.")
        print("Need at least 2 years of data to compute trends.")
        sys.exit(1)

    print(f"\nAnalyzing {len(trends)} SDGs...")

    # Setup output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter by SDG if specified
    if args.sdg:
        if args.sdg in trends:
            trends = {args.sdg: trends[args.sdg]}
            title += f" (SDG {args.sdg} Only)"
        else:
            print(f"\nWarning: SDG {args.sdg} not found in trends")
            return

    # Generate outputs
    output_files = {}

    # Summary DataFrame
    summary_df = trend_analyzer.get_trend_summary_dataframe(trends)

    print("\n" + "=" * 60)
    print("TREND SUMMARY")
    print("=" * 60)

    sig_increasing = summary_df[(summary_df['Significant'] == True) &
                                (summary_df['Trend Direction'] == 'increasing')]
    sig_decreasing = summary_df[(summary_df['Significant'] == True) &
                                (summary_df['Trend Direction'] == 'decreasing')]
    stable = summary_df[summary_df['Trend Direction'] == 'stable']

    print(f"\nTotal SDGs analyzed: {len(trends)}")
    print(f"Significant increasing trends: {len(sig_increasing)}")
    print(f"Significant decreasing trends: {len(sig_decreasing)}")
    print(f"Stable trends: {len(stable)}")

    if len(sig_increasing) > 0:
        print("\nSignificant Increasing Trends:")
        for _, row in sig_increasing.iterrows():
            print(f"  SDG {int(row['SDG'])} ({row['SDG Name']}): "
                  f"+{row['Percent Change']:.1f}% change")

    if len(sig_decreasing) > 0:
        print("\nSignificant Decreasing Trends:")
        for _, row in sig_decreasing.iterrows():
            print(f"  SDG {int(row['SDG'])} ({row['SDG Name']}): "
                  f"{row['Percent Change']:.1f}% change")

    # CSV output
    if args.format in ["all", "csv"]:
        csv_path = output_dir / "trend_summary.csv"
        summary_df.to_csv(csv_path, index=False)
        output_files['csv'] = csv_path
        print(f"\nCSV saved: {csv_path}")

    # Text report
    if args.format in ["all", "txt"] and not args.viz_only:
        report_path = trend_analyzer.export_trend_report(
            trends,
            output_path=output_dir / "trend_report.txt"
        )
        output_files['report'] = report_path
        print(f"Report saved: {report_path}")

    # Visualizations
    print("\n" + "=" * 60)
    print("GENERATING VISUALIZATIONS")
    print("=" * 60)

    # Line chart
    line_path = trend_analyzer.create_trend_visualization(
        trends,
        title=title,
        filename="trend_analysis.png",
        output_dir=output_dir
    )
    if line_path:
        output_files['line_chart'] = line_path
        print(f"Line chart: {line_path}")

    # Bar chart
    bar_path = trend_analyzer.create_trend_bar_chart(
        trends,
        title=title,
        filename="trend_bar_chart.png",
        output_dir=output_dir
    )
    if bar_path:
        output_files['bar_chart'] = bar_path
        print(f"Bar chart: {bar_path}")

    # Heatmap
    heatmap_path = trend_analyzer.create_trend_heatmap(
        trends,
        title=title,
        filename="trend_heatmap.png",
        output_dir=output_dir
    )
    if heatmap_path:
        output_files['heatmap'] = heatmap_path
        print(f"Heatmap: {heatmap_path}")

    print("\n" + "=" * 60)
    print("TREND ANALYSIS COMPLETE")
    print(f"Output directory: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
