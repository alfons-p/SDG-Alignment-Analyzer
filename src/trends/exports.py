"""Trend report exports module.

Contains methods for exporting trend analysis reports.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np

from src.trends.core import TrendResult, TrendAnalyzer
from src.trends.analysis import AnalysisMixin
from src.trends.visualizations import VisualizationMixin
from src.trends.comparison import ComparisonMixin
from src.config import SDG_DEFINITIONS


class ExportMixin(ComparisonMixin):
    """Mixin class providing trend export methods.

    Inherits from AnalysisMixin, VisualizationMixin, and ComparisonMixin
    to provide access to all trend analysis functionality.
    """

    def export_trend_report(self, trends: Dict[int, TrendResult],
                            output_path: Optional[Path] = None) -> Path:
        """
        Export a comprehensive trend analysis report.

        Args:
            trends: Dictionary mapping SDG number to TrendResult
            output_path: Path for output file (optional)

        Returns:
            Path to saved report
        """
        if output_path is None:
            results_dir = getattr(self, 'results_dir', Path('.'))
            output_dir = results_dir / "trends"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "trend_report.txt"

        with open(output_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("SDG TREND ANALYSIS REPORT\n")
            f.write("=" * 70 + "\n\n")

            # Overall summary
            significant_increasing = sum(1 for t in trends.values()
                                        if t.is_significant and t.trend_direction == 'increasing')
            significant_decreasing = sum(1 for t in trends.values()
                                          if t.is_significant and t.trend_direction == 'decreasing')
            stable = sum(1 for t in trends.values() if t.trend_direction == 'stable')

            f.write(f"Total SDGs analyzed: {len(trends)}\n")
            f.write(f"Significant increasing trends: {significant_increasing}\n")
            f.write(f"Significant decreasing trends: {significant_decreasing}\n")
            f.write(f"Stable trends: {stable}\n\n")

            # Detailed results
            f.write("-" * 70 + "\n")
            f.write("DETAILED SDG TRENDS\n")
            f.write("-" * 70 + "\n\n")

            for sdg_num in sorted(trends.keys()):
                trend = trends[sdg_num]
                f.write(f"\nSDG {sdg_num}: {trend.sdg_name}\n")
                f.write("-" * 40 + "\n")
                f.write(f"  Trend Direction: {trend.trend_direction.upper()}\n")
                f.write(f"  Statistical Significance: {'Yes' if trend.is_significant else 'No'} (p = {trend.p_value:.4f})\n")
                f.write(f"  Slope: {trend.trend_slope:.4f}\n")
                f.write(f"  R-squared: {trend.r_squared:.3f}\n")
                f.write(f"  Percent Change: {trend.percent_change:.1f}%\n")
                f.write(f"  Years: {', '.join(trend.years)}\n")
                f.write(f"  Scores: {', '.join([f'{s:.3f}' for s in trend.scores])}\n")

            # Top trends
            f.write("\n\n" + "=" * 70 + "\n")
            f.write("KEY FINDINGS\n")
            f.write("=" * 70 + "\n\n")

            # Sort by absolute slope
            sorted_trends = sorted(trends.values(), key=lambda t: abs(t.trend_slope), reverse=True)

            f.write("Top 5 Strongest Trends:\n")
            for i, trend in enumerate(sorted_trends[:5], 1):
                sig_marker = "*" if trend.is_significant else ""
                f.write(f"  {i}. SDG {trend.sdg} ({trend.sdg_name}): "
                       f"{trend.trend_direction} (slope: {trend.trend_slope:.4f}){sig_marker}\n")

        return output_path

    def export_state_comparison_report(self, state_trends: Dict[str, Dict[int, TrendResult]],
                                       output_path: Optional[Path] = None) -> Path:
        """
        Export a report comparing trends across states.

        Args:
            state_trends: Dictionary mapping state to trends dictionary
            output_path: Path for output file (optional)

        Returns:
            Path to saved report
        """
        if output_path is None:
            results_dir = getattr(self, 'results_dir', Path('.'))
            output_dir = results_dir / "trends"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "state_comparison_report.txt"

        states = sorted(state_trends.keys())

        with open(output_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("STATE-SPECIFIC SDG TREND ANALYSIS REPORT\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"States analyzed: {', '.join(states)}\n")
            f.write(f"Number of SDGs: 17\n\n")

            # Summary table by state
            f.write("-" * 70 + "\n")
            f.write("SUMMARY BY STATE\n")
            f.write("-" * 70 + "\n\n")

            for state in states:
                trends = state_trends[state]
                sig_increasing = sum(1 for t in trends.values()
                                    if t.is_significant and t.trend_direction == 'increasing')
                sig_decreasing = sum(1 for t in trends.values()
                                     if t.is_significant and t.trend_direction == 'decreasing')
                stable = sum(1 for t in trends.values() if t.trend_direction == 'stable')

                f.write(f"\n{state}:\n")
                f.write(f"  Significant increasing trends: {sig_increasing}\n")
                f.write(f"  Significant decreasing trends: {sig_decreasing}\n")
                f.write(f"  Stable trends: {stable}\n")

            # Detailed comparison for each SDG
            f.write("\n\n" + "=" * 70 + "\n")
            f.write("SDG-BY-SDG COMPARISON\n")
            f.write("=" * 70 + "\n\n")

            for sdg_num in range(1, 18):
                sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get('name', f'SDG {sdg_num}')
                f.write(f"\nSDG {sdg_num}: {sdg_name}\n")
                f.write("-" * 40 + "\n")

                for state in states:
                    if sdg_num in state_trends[state]:
                        trend = state_trends[state][sdg_num]
                        sig_marker = "*" if trend.is_significant else ""
                        f.write(f"  {state:6s}: {trend.trend_direction:12s} "
                               f"(slope: {trend.trend_slope:+.4f}, "
                               f"change: {trend.percent_change:+.1f}%){sig_marker}\n")

            # State rankings
            f.write("\n\n" + "=" * 70 + "\n")
            f.write("STATE RANKINGS BY AVERAGE TREND\n")
            f.write("=" * 70 + "\n\n")

            state_avg_slopes = {}
            for state, trends in state_trends.items():
                avg_slope = np.mean([t.trend_slope for t in trends.values()])
                state_avg_slopes[state] = avg_slope

            sorted_states = sorted(state_avg_slopes.items(), key=lambda x: x[1], reverse=True)
            f.write("Ranked by average trend slope:\n\n")
            for i, (state, avg_slope) in enumerate(sorted_states, 1):
                f.write(f"  {i}. {state}: {avg_slope:+.4f}\n")

        return output_path

    def generate_full_trend_analysis(self, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Generate a complete trend analysis with all visualizations.

        Args:
            output_dir: Directory for output files (optional)

        Returns:
            Dictionary mapping output type to file path
        """
        results_dir = getattr(self, 'results_dir', Path('.'))
        output_dir = output_dir or results_dir / "trends"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_files = {}

        # Overall trends
        overall_trends = self.analyze_overall_trends()
        if overall_trends:
            # Summary CSV
            summary_df = self.get_trend_summary_dataframe(overall_trends)
            summary_path = output_dir / "overall_trend_summary.csv"
            summary_df.to_csv(summary_path, index=False)
            output_files['overall_summary_csv'] = summary_path

            # Line chart
            line_path = self.create_trend_visualization(
                overall_trends,
                title="Overall SDG Trends (All Councils)",
                filename="overall_trends.png",
                output_dir=output_dir
            )
            output_files['overall_line_chart'] = line_path

            # Heatmap
            heatmap_path = self.create_trend_heatmap(
                overall_trends,
                title="Overall SDG Trend Metrics",
                filename="overall_trend_heatmap.png",
                output_dir=output_dir
            )
            output_files['overall_heatmap'] = heatmap_path

            # Bar chart
            bar_path = self.create_trend_bar_chart(
                overall_trends,
                title="Overall SDG Trend Slopes",
                filename="overall_trend_bars.png",
                output_dir=output_dir
            )
            output_files['overall_bar_chart'] = bar_path

            # Text report
            report_path = self.export_trend_report(
                overall_trends,
                output_path=output_dir / "overall_trend_report.txt"
            )
            output_files['overall_report'] = report_path

        return output_files

    def generate_state_trend_analysis(self, states: Optional[List[str]] = None,
                                      output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Generate a complete state-specific trend analysis.

        Args:
            states: List of states to analyze (optional, defaults to all available)
            output_dir: Directory for output files (optional)

        Returns:
            Dictionary mapping output type to file path
        """
        results_dir = getattr(self, 'results_dir', Path('.'))
        output_dir = output_dir or results_dir / "trends" / "by_state"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_files = {}

        # Get available states if not specified
        if states is None:
            states = self.get_available_states()

        if len(states) == 0:
            print("No states found in results")
            return output_files

        print(f"\nAnalyzing trends for states: {', '.join(states)}")

        # Analyze each state
        state_trends = self.analyze_multiple_states(states)

        # Individual state reports
        for state, trends in state_trends.items():
            if not trends:
                continue

            state_dir = output_dir / state.lower()
            state_dir.mkdir(parents=True, exist_ok=True)

            # Summary CSV
            summary_df = self.get_trend_summary_dataframe(trends)
            summary_path = state_dir / f"{state.lower()}_trend_summary.csv"
            summary_df.to_csv(summary_path, index=False)
            output_files[f'{state}_summary_csv'] = summary_path

            # Line chart
            line_path = self.create_trend_visualization(
                trends,
                title=f"SDG Trends for {state}",
                filename=f"{state.lower()}_trends.png",
                output_dir=state_dir
            )
            output_files[f'{state}_line_chart'] = line_path

            # Bar chart
            bar_path = self.create_trend_bar_chart(
                trends,
                title=f"SDG Trend Slopes for {state}",
                filename=f"{state.lower()}_trend_bars.png",
                output_dir=state_dir
            )
            output_files[f'{state}_bar_chart'] = bar_path

            # Text report
            report_path = self.export_trend_report(
                trends,
                output_path=state_dir / f"{state.lower()}_trend_report.txt"
            )
            output_files[f'{state}_report'] = report_path

        # State comparison (if multiple states)
        if len(state_trends) >= 2:
            print(f"\nGenerating state comparison for {len(state_trends)} states...")

            # Comparison visualization
            comparison_path = self.create_state_comparison_visualization(
                state_trends,
                title=f"State Comparison: {' vs '.join(states)}",
                filename="state_comparison_trends.png",
                output_dir=output_dir
            )
            output_files['state_comparison_chart'] = comparison_path

            # Comparison bar chart
            comparison_bar_path = self.create_state_comparison_bar_chart(
                state_trends,
                title=f"State Comparison: Trend Slopes ({' vs '.join(states)})",
                filename="state_comparison_slopes.png",
                output_dir=output_dir
            )
            output_files['state_comparison_bars'] = comparison_bar_path

            # Comparison report
            comparison_report_path = self.export_state_comparison_report(
                state_trends,
                output_path=output_dir / "state_comparison_report.txt"
            )
            output_files['state_comparison_report'] = comparison_report_path

        return output_files
