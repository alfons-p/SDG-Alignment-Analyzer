"""Matplotlib-based visualization module.

Contains static visualization methods using matplotlib and seaborn.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from matplotlib.figure import Figure

# Suppress font glyph warnings (non-critical)
warnings.filterwarnings("ignore", category=UserWarning, module="seaborn.utils")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

from src.config import Config, SDG_DEFINITIONS
from src.sdg_reference import SDGReference


class VisualizationMixin:
    """Mixin class providing matplotlib visualization methods.

    This class provides visualization methods that can be mixed into Reporter.
    """

    def create_heatmap(
        self,
        results: Dict[str, Any],
        filename: Optional[str] = None,
        top_n_activities: int = 50
    ) -> Path:
        """
        Create heatmap of activities vs SDGs.

        Args:
            results: Alignment results
            filename: Output filename
            top_n_activities: Number of top activities to show

        Returns:
            Path to saved figure
        """
        activities = results.get("activities", [])
        if not activities:
            raise ValueError("No activities in results")

        # Sort by relevance and take top N
        sorted_activities = sorted(
            activities,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )[:top_n_activities]

        # Build matrix
        matrix = np.zeros((len(sorted_activities), 17))
        activity_labels = []

        for i, activity in enumerate(sorted_activities):
            activity_labels.append(activity["activity_text"][:50] + "...")
            for sdg_num in range(1, 18):
                sdg_scores = activity["sdg_scores"]
                score = sdg_scores.get(sdg_num, sdg_scores.get(str(sdg_num), {})).get("score", 0)
                matrix[i, sdg_num - 1] = score

        # Create figure
        fig, ax = plt.subplots(figsize=(14, max(8, len(sorted_activities) * 0.3)))

        # Create heatmap
        sns.heatmap(
            matrix,
            xticklabels=[f"SDG {i}" for i in range(1, 18)],
            yticklabels=activity_labels,
            cmap="YlOrRd",
            vmin=0,
            vmax=1,
            cbar_kws={"label": "Similarity Score"},
            ax=ax,
            linewidths=0.5,
            linecolor='white'
        )

        ax.set_title(
            f"SDG Alignment Heatmap - {Path(results.get('source', 'Report')).name}",
            fontsize=14,
            pad=20
        )
        ax.set_xlabel("Sustainable Development Goals", fontsize=12)
        ax.set_ylabel("Activities", fontsize=12)

        plt.tight_layout()

        # Save
        if filename is None:
            source_name = Path(results.get("source", "report")).stem
            filename = f"{source_name}_heatmap.png"

        # Access the council_output_dir from the parent Reporter class
        council_output_dir = getattr(self, 'council_output_dir', Path('.'))
        output_path = council_output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def create_radar_chart(
        self,
        results: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """
        Create radar chart of SDG alignment profile.

        Args:
            results: Alignment results
            filename: Output filename

        Returns:
            Path to saved figure
        """
        report = results.get("report_alignment", {})
        mean_scores = report.get("mean_scores", {})

        # Prepare data
        categories = [f"SDG {i}" for i in range(1, 18)]
        values = [mean_scores.get(i, 0) for i in range(1, 18)]

        # Number of variables
        N = len(categories)

        # Compute angle for each axis
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        values += values[:1]
        angles += angles[:1]

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

        # Draw lines
        ax.plot(angles, values, 'o-', linewidth=2, color='#1f77b4', alpha=0.8)
        ax.fill(angles, values, alpha=0.25, color='#1f77b4')

        # Add labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=10)

        # Set y limits
        ax.set_ylim(0, max(values) * 1.1)

        # Add title
        source_name = Path(results.get("source", "Report")).name
        ax.set_title(
            f"SDG Alignment Profile\n{source_name}",
            size=14,
            y=1.08
        )

        plt.tight_layout()

        # Save
        if filename is None:
            filename = f"{Path(results.get('source', 'report')).stem}_radar.png"

        council_output_dir = getattr(self, 'council_output_dir', Path('.'))
        output_path = council_output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def create_bar_chart(
        self,
        results: Dict[str, Any],
        filename: Optional[str] = None,
        top_n: int = 10
    ) -> Path:
        """
        Create bar chart of top SDGs.

        Args:
            results: Alignment results
            filename: Output filename
            top_n: Number of SDGs to show

        Returns:
            Path to saved figure
        """
        report = results.get("report_alignment", {})
        top_sdgs = report.get("top_sdgs", [])[:top_n]

        if not top_sdgs:
            raise ValueError("No SDG data to plot")

        # Prepare data
        sdg_nums = [s['sdg'] for s in top_sdgs]
        scores = [s['mean_score'] for s in top_sdgs]
        names = [s['name'] for s in top_sdgs]
        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        colors = [sdg_reference.get_sdg_color(s['sdg']) for s in top_sdgs]

        # Create combined labels: SDG number + short name
        max_name_len = 35
        y_labels = []
        for sdg_num, name in zip(sdg_nums, names):
            short_name = name[:max_name_len] + "..." if len(name) > max_name_len else name
            y_labels.append(f"SDG {sdg_num}: {short_name}")

        # Create figure with more height for labels
        fig, ax = plt.subplots(figsize=(14, max(6, len(top_sdgs) * 0.6)))

        bars = ax.barh(y_labels, scores, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)

        # Add score labels
        for bar, score in zip(bars, scores):
            width = bar.get_width()
            ax.text(
                width + 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'{score:.3f}',
                ha='left',
                va='center',
                fontsize=9
            )

        ax.set_xlabel('Mean Alignment Score', fontsize=12)
        ax.set_ylabel('')
        ax.set_title(
            f"Top {top_n} SDGs by Alignment Score\n{Path(results.get('source', 'Report')).name}",
            fontsize=14,
            pad=20
        )

        ax.set_xlim(0, max(scores) * 1.15)
        ax.invert_yaxis()

        # Adjust layout to fit labels
        plt.tight_layout()
        plt.subplots_adjust(left=0.35)  # Make room for y-labels

        # Save
        if filename is None:
            filename = f"{Path(results.get('source', 'report')).stem}_top_sdgs.png"

        council_output_dir = getattr(self, 'council_output_dir', Path('.'))
        output_path = council_output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def create_comparison_charts(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Create comparison charts for multiple reports - both box-plot and bar chart.

        Generates two charts:
        1. Box-plot showing distribution of alignment scores across councils per SDG
        2. Bar chart showing mean alignment scores per SDG (with Urban/Rural grouping if available)

        Args:
            results_list: List of alignment results from multiple reports
            filename_prefix: Prefix for output filenames (e.g., "comparison" -> "comparison_boxplot.png")

        Returns:
            Dictionary with paths to saved figures: {"boxplot": Path, "bar_chart": Path}
        """
        if not results_list or len(results_list) < 2:
            raise ValueError("Need at least 2 reports to compare")

        if filename_prefix is None:
            filename_prefix = "comparison"

        output_paths = {}

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())

        # Prepare data - collect all activities with their SDG scores
        sdg_nums = list(range(1, 18))
        sdg_names = [f"SDG {i}\n{sdg_reference.get_sdg_name(i)[:15]}" for i in sdg_nums]

        # Data for box plot: list of scores per SDG across all councils
        sdg_scores_data = {i: [] for i in sdg_nums}

        # Group councils by Urban/Rural classification
        urban_results = []
        rural_results = []
        unknown_results = []

        for result in results_list:
            urban_rural = result.get("metadata", {}).get("urban_rural", "Unknown")
            if urban_rural == "Urban":
                urban_results.append(result)
            elif urban_rural == "Rural":
                rural_results.append(result)
            else:
                unknown_results.append(result)

        has_urban_rural = len(urban_results) > 0 and len(rural_results) > 0

        # Collect mean scores by classification
        urban_means = {}
        rural_means = {}
        all_means = {}

        for result in results_list:
            report = result.get("report_alignment", {})
            mean_scores = report.get("mean_scores", {})
            source_name = Path(result.get("source", "Unknown")).stem[:20]
            council_means_list = [mean_scores.get(i, 0) for i in sdg_nums]

            all_means[source_name] = council_means_list

            urban_rural = result.get("metadata", {}).get("urban_rural", "Unknown")
            if urban_rural == "Urban":
                urban_means[source_name] = council_means_list
            elif urban_rural == "Rural":
                rural_means[source_name] = council_means_list

            # Collect individual activity scores for box plot
            activities = result.get("activities", [])
            for activity in activities:
                for sdg_num in sdg_nums:
                    sdg_scores = activity["sdg_scores"]
                    score = sdg_scores.get(sdg_num, sdg_scores.get(str(sdg_num), {})).get("score", 0)
                    sdg_scores_data[sdg_num].append(score)

        # ========== CHART 1: BOX PLOT (Distribution) ==========
        fig1, ax1 = plt.subplots(figsize=(16, 8))

        # Prepare data for box plot
        box_data = [sdg_scores_data[i] for i in sdg_nums]
        bp = ax1.boxplot(box_data, labels=sdg_names, patch_artist=True, showmeans=True)

        # Color the boxes
        for patch, sdg_num in zip(bp['boxes'], sdg_nums):
            patch.set_facecolor(sdg_reference.get_sdg_color(sdg_num))
            patch.set_alpha(0.6)

        ax1.set_xlabel('Sustainable Development Goals', fontsize=12)
        ax1.set_ylabel('Alignment Score Distribution', fontsize=12)
        ax1.set_title('SDG Alignment Score Distribution Across All Councils\n(Box Plot: Median, Quartiles, and Outliers)',
                      fontsize=14, pad=20)

        # Calculate dynamic Y-axis limit based on data
        _calculate_y_axis_limit = getattr(self, '_calculate_y_axis_limit', lambda x, y: max(x) * 1.1 if x else 1.0)
        all_scores = [score for scores in box_data for score in scores]
        y_max = _calculate_y_axis_limit(all_scores, is_percentage=False)
        ax1.set_ylim(0, y_max)
        ax1.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Rotate x labels
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        # Save box plot
        output_dir = getattr(self, 'output_dir', Path('.'))
        boxplot_path = output_dir / f"{filename_prefix}_boxplot.png"
        plt.savefig(boxplot_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["boxplot"] = boxplot_path

        # ========== CHART 2: BAR CHART (Mean Scores Across Councils) ==========
        fig2, ax2 = plt.subplots(figsize=(16, 8))

        x = np.arange(len(sdg_nums))

        if has_urban_rural:
            # Calculate mean scores for Urban and Rural separately
            urban_mean_scores = []
            rural_mean_scores = []

            for sdg_num in sdg_nums:
                # Urban means
                urban_scores = [urban_means[name][sdg_num - 1] for name in urban_means.keys()]
                urban_mean = np.mean(urban_scores) if urban_scores else 0
                urban_mean_scores.append(urban_mean)

                # Rural means
                rural_scores = [rural_means[name][sdg_num - 1] for name in rural_means.keys()]
                rural_mean = np.mean(rural_scores) if rural_scores else 0
                rural_mean_scores.append(rural_mean)

            width = 0.35

            # Get colors for each SDG (darker for urban, lighter for rural)
            urban_colors = [sdg_reference.get_sdg_color(i) for i in sdg_nums]
            rural_colors = [sdg_reference.get_sdg_color(i) for i in sdg_nums]

            # Create grouped bars
            bars1 = ax2.bar(x - width/2, urban_mean_scores, width, label='Urban',
                           color=urban_colors, alpha=0.9, edgecolor='black', linewidth=0.5)
            bars2 = ax2.bar(x + width/2, rural_mean_scores, width, label='Rural',
                           color=rural_colors, alpha=0.6, edgecolor='black', linewidth=0.5, hatch='//')

            # Add value labels on top of bars
            for bar, mean_score in zip(bars1, urban_mean_scores):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 0.01,
                    f'{mean_score:.3f}',
                    ha='center',
                    va='bottom',
                    fontsize=7
                )
            for bar, mean_score in zip(bars2, rural_mean_scores):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 0.01,
                    f'{mean_score:.3f}',
                    ha='center',
                    va='bottom',
                    fontsize=7
                )

            ax2.legend(loc='upper right', title='Council Type')
            title_text = 'SDG Alignment - Mean Across Urban vs Rural Councils'
        else:
            # Original single bar behavior
            mean_scores = []
            for sdg_num in sdg_nums:
                scores_for_sdg = [all_means[name][sdg_num - 1] for name in all_means.keys()]
                mean_score = np.mean(scores_for_sdg) if scores_for_sdg else 0
                mean_scores.append(mean_score)

            bar_colors = [sdg_reference.get_sdg_color(i) for i in sdg_nums]
            bars = ax2.bar(x, mean_scores, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=0.5)

            for bar, mean_score in zip(bars, mean_scores):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 0.01,
                    f'{mean_score:.3f}',
                    ha='center',
                    va='bottom',
                    fontsize=8
                )
            title_text = 'SDG Alignment - Mean Across All Councils'

        ax2.set_xlabel('Sustainable Development Goals', fontsize=12)
        ax2.set_ylabel('Mean Alignment Score', fontsize=12)
        ax2.set_title(title_text, fontsize=14, pad=20)
        ax2.set_xticks(x)
        ax2.set_xticklabels([f"SDG {i}" for i in sdg_nums], rotation=45, ha='right')
        ax2.yaxis.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()

        # Save bar chart
        bar_path = output_dir / f"{filename_prefix}_bar.png"
        plt.savefig(bar_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["bar_chart"] = bar_path

        return output_paths

    def create_comparison_chart(
        self,
        results_list: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Path:
        """
        Create comparison bar chart for multiple reports (legacy method).

        DEPRECATED: Use create_comparison_charts() instead for both box-plot and bar chart.

        Args:
            results_list: List of alignment results from multiple reports
            filename: Output filename

        Returns:
            Path to saved figure
        """
        output_paths = self.create_comparison_charts(results_list, filename_prefix="comparison")
        return output_paths["bar_chart"]

    def create_coverage_comparison_charts(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: Optional[str] = None,
        sort_by: str = "sdg"
    ) -> Dict[str, Path]:
        """
        Create coverage comparison charts - both box-plot and bar chart.

        Generates two charts:
        1. Box-plot showing distribution of coverage across councils per SDG
        2. Bar chart showing mean coverage per SDG (with Urban/Rural grouping if available)

        Args:
            results_list: List of alignment results
            filename_prefix: Prefix for output filenames
            sort_by: "coverage" to sort by average coverage, "sdg" for SDG number

        Returns:
            Dictionary with paths to saved figures: {"boxplot": Path, "bar_chart": Path}
        """
        if not results_list or len(results_list) < 1:
            raise ValueError("Need at least 1 report to create chart")

        if filename_prefix is None:
            filename_prefix = "coverage_comparison"

        output_paths = {}

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        _calculate_y_axis_limit = getattr(self, '_calculate_y_axis_limit', lambda x, y: max(x) * 1.1 if x else 1.0)

        # Prepare data for all SDGs (1-17)
        sdg_nums = list(range(1, 18))
        sdg_names = [f"SDG {i}\n{sdg_reference.get_sdg_name(i)[:12]}" for i in sdg_nums]
        sdg_colors = [sdg_reference.get_sdg_color(i) for i in sdg_nums]

        # Group results by Urban/Rural classification
        urban_results = []
        rural_results = []

        for result in results_list:
            urban_rural = result.get("metadata", {}).get("urban_rural", "Unknown")
            if urban_rural == "Urban":
                urban_results.append(result)
            elif urban_rural == "Rural":
                rural_results.append(result)

        has_urban_rural = len(urban_results) > 0 and len(rural_results) > 0

        # Collect coverage data per SDG across all councils
        sdg_coverage_data = {i: [] for i in sdg_nums}
        sdg_coverage_urban = {i: [] for i in sdg_nums}
        sdg_coverage_rural = {i: [] for i in sdg_nums}
        council_coverage = {}

        for result in results_list:
            report = result.get("report_alignment", {})
            coverage = report.get("coverage", {})
            metadata = result.get("metadata", {})

            # Build council label
            base_name = Path(result.get("source", "Unknown")).stem[:15]
            year = metadata.get("year", "")
            state = metadata.get("state", "")

            if year and state:
                source_name = f"{base_name} ({state} {year})"
            elif year:
                source_name = f"{base_name} ({year})"
            elif state:
                source_name = f"{base_name} ({state})"
            else:
                source_name = base_name

            council_coverage[source_name] = []

            urban_rural = metadata.get("urban_rural", "Unknown")

            for sdg_num in sdg_nums:
                # Handle both integer and string keys in coverage dict
                cov = coverage.get(sdg_num, coverage.get(str(sdg_num), 0.0))
                cov_pct = cov * 100  # Convert to percentage
                sdg_coverage_data[sdg_num].append(cov_pct)
                council_coverage[source_name].append(cov_pct)

                # Also add to urban or rural specific data
                if urban_rural == "Urban":
                    sdg_coverage_urban[sdg_num].append(cov_pct)
                elif urban_rural == "Rural":
                    sdg_coverage_rural[sdg_num].append(cov_pct)

        # Calculate average coverage per SDG
        sdg_coverage_avg = {i: np.mean(sdg_coverage_data[i]) for i in sdg_nums}

        # Determine sort order
        if sort_by == "coverage":
            sorted_sdgs = sorted(sdg_coverage_avg.keys(), key=lambda x: sdg_coverage_avg[x], reverse=True)
        else:
            sorted_sdgs = sdg_nums

        # ========== CHART 1: BOX PLOT (Distribution) ==========
        fig1, ax1 = plt.subplots(figsize=(16, 8))

        # Prepare data in sorted order
        box_data = [sdg_coverage_data[i] for i in sorted_sdgs]
        sorted_names = [sdg_names[i - 1] for i in sorted_sdgs]
        sorted_colors = [sdg_colors[i - 1] for i in sorted_sdgs]

        bp = ax1.boxplot(box_data, labels=sorted_names, patch_artist=True, showmeans=True)

        # Color the boxes
        for patch, color in zip(bp['boxes'], sorted_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax1.set_xlabel("Sustainable Development Goals", fontsize=12)
        ax1.set_ylabel("Coverage (% of Activities Aligned)", fontsize=12)
        ax1.set_title(
            "SDG Coverage Distribution Across Councils\n(Box Plot: Median, Quartiles, and Outliers)",
            fontsize=14,
            pad=20
        )
        # Calculate dynamic Y-axis limit based on data
        all_coverage = [cov for coverages in box_data for cov in coverages]
        y_max = _calculate_y_axis_limit(all_coverage, is_percentage=True)
        ax1.set_ylim(0, y_max)
        ax1.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Rotate x labels
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        # Save box plot
        output_dir = getattr(self, 'output_dir', Path('.'))
        boxplot_path = output_dir / f"{filename_prefix}_boxplot.png"
        plt.savefig(boxplot_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["boxplot"] = boxplot_path

        # ========== CHART 2: BAR CHART (Mean Coverage Across Councils) ==========
        fig2, ax2 = plt.subplots(figsize=(16, 8))

        x = np.arange(len(sorted_sdgs))

        if has_urban_rural:
            # Calculate mean coverage for Urban and Rural separately
            urban_mean_coverages = []
            rural_mean_coverages = []

            for sdg_num in sorted_sdgs:
                urban_covs = sdg_coverage_urban[sdg_num]
                rural_covs = sdg_coverage_rural[sdg_num]

                urban_mean = np.mean(urban_covs) if urban_covs else 0
                rural_mean = np.mean(rural_covs) if rural_covs else 0

                urban_mean_coverages.append(urban_mean)
                rural_mean_coverages.append(rural_mean)

            width = 0.35

            # Get colors for each SDG
            bar_colors = [sdg_colors[i - 1] for i in sorted_sdgs]

            # Create grouped bars
            bars1 = ax2.bar(x - width/2, urban_mean_coverages, width, label='Urban',
                           color=bar_colors, alpha=0.9, edgecolor='black', linewidth=0.5)
            bars2 = ax2.bar(x + width/2, rural_mean_coverages, width, label='Rural',
                           color=bar_colors, alpha=0.6, edgecolor='black', linewidth=0.5, hatch='//')

            # Add value labels on top of bars
            for bar, mean_cov in zip(bars1, urban_mean_coverages):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 1,
                    f'{mean_cov:.1f}%',
                    ha='center',
                    va='bottom',
                    fontsize=7
                )
            for bar, mean_cov in zip(bars2, rural_mean_coverages):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 1,
                    f'{mean_cov:.1f}%',
                    ha='center',
                    va='bottom',
                    fontsize=7
                )

            ax2.legend(loc='upper right', title='Council Type')
            title_text = "SDG Coverage - Mean Across Urban vs Rural Councils"
            all_coverages = urban_mean_coverages + rural_mean_coverages
        else:
            # Original single bar behavior
            mean_coverages = []
            for sdg_num in sorted_sdgs:
                sdg_coverages = sdg_coverage_data[sdg_num]
                mean_coverage = np.mean(sdg_coverages) if sdg_coverages else 0
                mean_coverages.append(mean_coverage)

            bar_colors = [sdg_colors[i - 1] for i in sorted_sdgs]
            bars = ax2.bar(x, mean_coverages, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=0.5)

            for bar, mean_cov in zip(bars, mean_coverages):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + 1,
                    f'{mean_cov:.1f}%',
                    ha='center',
                    va='bottom',
                    fontsize=8
                )
            title_text = "SDG Coverage - Mean Across All Councils"
            all_coverages = mean_coverages

        ax2.set_xlabel("Sustainable Development Goals", fontsize=12)
        ax2.set_ylabel("Mean Coverage (% of Activities Aligned)", fontsize=12)
        ax2.set_title(title_text, fontsize=14, pad=20)
        ax2.set_xticks(x)
        ax2.set_xticklabels([f"SDG {i}" for i in sorted_sdgs], rotation=45, ha='right')
        ax2.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Set dynamic Y-axis limit based on data
        y_max = _calculate_y_axis_limit(all_coverages, is_percentage=True)
        ax2.set_ylim(0, y_max)

        plt.tight_layout()

        # Save bar chart
        bar_path = output_dir / f"{filename_prefix}_bar.png"
        plt.savefig(bar_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["bar_chart"] = bar_path

        return output_paths

    def create_coverage_comparison_chart(
        self,
        results_list: List[Dict[str, Any]],
        filename: Optional[str] = None,
        sort_by: str = "sdg"
    ) -> Path:
        """
        Create coverage comparison bar chart (legacy method).

        DEPRECATED: Use create_coverage_comparison_charts() for both box-plot and bar chart.

        Args:
            results_list: List of alignment results
            filename: Output filename (optional)
            sort_by: "coverage" to sort by average coverage, "sdg" for SDG number

        Returns:
            Path to saved figure
        """
        output_paths = self.create_coverage_comparison_charts(
            results_list,
            filename_prefix="coverage_comparison",
            sort_by=sort_by
        )
        return output_paths["bar_chart"]

    def create_yearly_comparison_charts(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Create yearly comparison charts showing mean alignment scores per SDG by year.

        Generates two charts:
        1. Grouped bar chart showing mean alignment scores per SDG for each year
        2. Line chart showing trends over time for each SDG

        Args:
            results_list: List of alignment results from multiple reports
            filename_prefix: Prefix for output filenames (e.g., "yearly" -> "yearly_alignment.png")

        Returns:
            Dictionary with paths to saved figures: {"bar_chart": Path, "line_chart": Path}
        """
        if not results_list:
            raise ValueError("Need at least 1 report to create chart")

        if filename_prefix is None:
            filename_prefix = "yearly_comparison"

        output_paths = {}

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        output_dir = getattr(self, 'output_dir', Path('.'))

        # Group results by year
        from collections import defaultdict
        year_results = defaultdict(list)
        for result in results_list:
            year = result.get("metadata", {}).get("year", "Unknown")
            year_results[year].append(result)

        if len(year_results) < 1:
            raise ValueError("No valid years found in results")

        sorted_years = sorted(year_results.keys())
        sdg_nums = list(range(1, 18))

        # Calculate mean scores per SDG per year
        yearly_scores = {}
        for year in sorted_years:
            yearly_scores[year] = {}
            for sdg_num in sdg_nums:
                scores = []
                for result in year_results[year]:
                    report = result.get("report_alignment", {})
                    mean_scores = report.get("mean_scores", {})
                    score = mean_scores.get(sdg_num, mean_scores.get(str(sdg_num), 0))
                    scores.append(score)
                yearly_scores[year][sdg_num] = np.mean(scores) if scores else 0.0

        # ========== CHART 1: GROUPED BAR CHART ==========
        fig1, ax1 = plt.subplots(figsize=(18, 8))

        x = np.arange(len(sdg_nums))
        width = 0.8 / len(sorted_years)

        # Define colors for years
        year_colors = plt.cm.viridis(np.linspace(0, 1, len(sorted_years)))

        for i, year in enumerate(sorted_years):
            scores = [yearly_scores[year][sdg_num] for sdg_num in sdg_nums]
            offset = width * (i - len(sorted_years) / 2 + 0.5)
            ax1.bar(x + offset, scores, width, label=f"Year {year}",
                   color=year_colors[i], alpha=0.8, edgecolor='black', linewidth=0.5)

        ax1.set_xlabel('Sustainable Development Goals', fontsize=12)
        ax1.set_ylabel('Mean Alignment Score', fontsize=12)
        ax1.set_title('SDG Alignment by Year - Mean Scores Comparison', fontsize=14, pad=20)
        ax1.set_xticks(x)
        ax1.set_xticklabels([f"SDG {i}" for i in sdg_nums], rotation=45, ha='right')
        ax1.legend(loc='upper right')
        ax1.yaxis.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()

        bar_path = output_dir / f"{filename_prefix}_bar.png"
        plt.savefig(bar_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["bar_chart"] = bar_path

        # ========== CHART 2: LINE CHART SHOWING TRENDS ==========
        fig2, ax2 = plt.subplots(figsize=(16, 8))

        for sdg_num in sdg_nums:
            sdg_name = sdg_reference.get_sdg_name(sdg_num)
            color = sdg_reference.get_sdg_color(sdg_num)
            scores = [yearly_scores[year][sdg_num] for year in sorted_years]

            ax2.plot(sorted_years, scores, marker='o', markersize=6,
                    label=f"SDG {sdg_num}: {sdg_name[:20]}",
                    color=color, linewidth=2, alpha=0.8)

        ax2.set_xlabel('Year', fontsize=12)
        ax2.set_ylabel('Mean Alignment Score', fontsize=12)
        ax2.set_title('SDG Alignment Trends Over Time', fontsize=14, pad=20)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax2.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax2.set_ylim(0, 1.0)

        plt.tight_layout()

        line_path = output_dir / f"{filename_prefix}_line.png"
        plt.savefig(line_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["line_chart"] = line_path

        return output_paths

    def create_yearly_coverage_comparison_charts(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Create yearly coverage comparison charts showing coverage % per SDG by year.

        Generates two charts:
        1. Grouped bar chart showing mean coverage % per SDG for each year
        2. Line chart showing coverage trends over time for each SDG

        Args:
            results_list: List of alignment results from multiple reports
            filename_prefix: Prefix for output filenames (e.g., "yearly" -> "yearly_coverage.png")

        Returns:
            Dictionary with paths to saved figures: {"bar_chart": Path, "line_chart": Path}
        """
        if not results_list:
            raise ValueError("Need at least 1 report to create chart")

        if filename_prefix is None:
            filename_prefix = "yearly_coverage"

        output_paths = {}

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        output_dir = getattr(self, 'output_dir', Path('.'))

        # Group results by year
        from collections import defaultdict
        year_results = defaultdict(list)
        for result in results_list:
            year = result.get("metadata", {}).get("year", "Unknown")
            year_results[year].append(result)

        if len(year_results) < 1:
            raise ValueError("No valid years found in results")

        sorted_years = sorted(year_results.keys())
        sdg_nums = list(range(1, 18))

        # Calculate mean coverage per SDG per year
        yearly_coverage = {}
        for year in sorted_years:
            yearly_coverage[year] = {}
            for sdg_num in sdg_nums:
                coverages = []
                for result in year_results[year]:
                    report = result.get("report_alignment", {})
                    coverage_dict = report.get("coverage", {})
                    cov = coverage_dict.get(sdg_num, coverage_dict.get(str(sdg_num), 0.0))
                    coverages.append(cov * 100)  # Convert to percentage
                yearly_coverage[year][sdg_num] = np.mean(coverages) if coverages else 0.0

        # ========== CHART 1: GROUPED BAR CHART ==========
        fig1, ax1 = plt.subplots(figsize=(18, 8))

        x = np.arange(len(sdg_nums))
        width = 0.8 / len(sorted_years)

        # Define colors for years
        year_colors = plt.cm.plasma(np.linspace(0, 1, len(sorted_years)))

        for i, year in enumerate(sorted_years):
            coverages = [yearly_coverage[year][sdg_num] for sdg_num in sdg_nums]
            offset = width * (i - len(sorted_years) / 2 + 0.5)
            ax1.bar(x + offset, coverages, width, label=f"Year {year}",
                   color=year_colors[i], alpha=0.8, edgecolor='black', linewidth=0.5)

        ax1.set_xlabel('Sustainable Development Goals', fontsize=12)
        ax1.set_ylabel('Mean Coverage (% of Activities Aligned)', fontsize=12)
        ax1.set_title('SDG Coverage by Year - Mean Coverage Comparison', fontsize=14, pad=20)
        ax1.set_xticks(x)
        ax1.set_xticklabels([f"SDG {i}" for i in sdg_nums], rotation=45, ha='right')
        ax1.legend(loc='upper right')
        ax1.yaxis.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()

        bar_path = output_dir / f"{filename_prefix}_bar.png"
        plt.savefig(bar_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["bar_chart"] = bar_path

        # ========== CHART 2: LINE CHART SHOWING COVERAGE TRENDS ==========
        fig2, ax2 = plt.subplots(figsize=(16, 8))

        for sdg_num in sdg_nums:
            sdg_name = sdg_reference.get_sdg_name(sdg_num)
            color = sdg_reference.get_sdg_color(sdg_num)
            coverages = [yearly_coverage[year][sdg_num] for year in sorted_years]

            ax2.plot(sorted_years, coverages, marker='o', markersize=6,
                    label=f"SDG {sdg_num}: {sdg_name[:20]}",
                    color=color, linewidth=2, alpha=0.8)

        ax2.set_xlabel('Year', fontsize=12)
        ax2.set_ylabel('Mean Coverage (% of Activities Aligned)', fontsize=12)
        ax2.set_title('SDG Coverage Trends Over Time', fontsize=14, pad=20)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax2.yaxis.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()

        line_path = output_dir / f"{filename_prefix}_line.png"
        plt.savefig(line_path, dpi=300, bbox_inches='tight')
        plt.close()
        output_paths["line_chart"] = line_path

        return output_paths

    def create_yearly_mean_comparison_bar_chart(
        self,
        results_list: List[Dict[str, Any]],
        filename: Optional[str] = None,
        sort_by: str = "sdg"
    ) -> Path:
        """
        Create a bar chart comparing mean alignment scores per SDG across years.

        Similar to create_comparison_chart() but shows yearly averages grouped by SDG,
        with bars for each year side-by-side.

        Args:
            results_list: List of alignment results from multiple reports/years
            filename: Output filename (optional)
            sort_by: "coverage" to sort by average, "sdg" for SDG number

        Returns:
            Path to saved figure
        """
        if not results_list:
            raise ValueError("Need at least 1 report to create chart")

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        output_dir = getattr(self, 'output_dir', Path('.'))
        _calculate_y_axis_limit = getattr(self, '_calculate_y_axis_limit', lambda x, y: max(x) * 1.1 if x else 1.0)

        # Group results by year
        from collections import defaultdict
        year_results = defaultdict(list)
        for result in results_list:
            year = result.get("metadata", {}).get("year", "Unknown")
            year_results[year].append(result)

        if len(year_results) < 1:
            raise ValueError("No valid years found in results")

        sorted_years = sorted(year_results.keys())
        sdg_nums = list(range(1, 18))
        sdg_names = [f"SDG {i}\n{sdg_reference.get_sdg_name(i)[:15]}" for i in sdg_nums]
        sdg_colors = [sdg_reference.get_sdg_color(i) for i in sdg_nums]

        # Calculate mean scores per SDG per year
        yearly_scores = {}
        for year in sorted_years:
            yearly_scores[year] = {}
            for sdg_num in sdg_nums:
                scores = []
                for result in year_results[year]:
                    report = result.get("report_alignment", {})
                    mean_scores = report.get("mean_scores", {})
                    score = mean_scores.get(sdg_num, mean_scores.get(str(sdg_num), 0))
                    scores.append(score)
                yearly_scores[year][sdg_num] = np.mean(scores) if scores else 0.0

        # Calculate overall mean per SDG for sorting
        sdg_means = {sdg_num: np.mean([yearly_scores[year][sdg_num] for year in sorted_years])
                     for sdg_num in sdg_nums}

        # Determine sort order
        if sort_by == "coverage":
            sorted_sdgs = sorted(sdg_nums, key=lambda x: sdg_means[x], reverse=True)
        else:
            sorted_sdgs = sdg_nums

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 8))

        x = np.arange(len(sorted_sdgs))
        width = 0.8 / len(sorted_years)

        # Define colors for years
        year_colors = plt.cm.viridis(np.linspace(0, 1, len(sorted_years)))

        # Create bars for each year
        for i, year in enumerate(sorted_years):
            scores = [yearly_scores[year][sdg_num] for sdg_num in sorted_sdgs]
            offset = width * (i - len(sorted_years) / 2 + 0.5)
            bars = ax.bar(x + offset, scores, width, label=f"Year {year}",
                         color=year_colors[i], alpha=0.8, edgecolor='black', linewidth=0.5)

            # Add value labels on top of bars
            for bar, score in zip(bars, scores):
                height = bar.get_height()
                if height > 0.01:  # Only label non-zero bars
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height + 0.01,
                        f'{score:.3f}',
                        ha='center',
                        va='bottom',
                        fontsize=6,
                        rotation=90
                    )

        ax.set_xlabel('Sustainable Development Goals', fontsize=12)
        ax.set_ylabel('Mean Alignment Score', fontsize=12)
        ax.set_title(f'SDG Alignment by Year - Mean Scores Comparison\n({len(sorted_years)} years)', fontsize=14, pad=20)
        ax.set_xticks(x)
        sorted_labels = [f"SDG {i}" for i in sorted_sdgs]
        ax.set_xticklabels(sorted_labels, rotation=45, ha='right')
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), framealpha=0.9)
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Set dynamic Y-axis limit
        all_scores = [yearly_scores[year][sdg_num] for year in sorted_years for sdg_num in sdg_nums]
        y_max = _calculate_y_axis_limit(all_scores, is_percentage=False)
        ax.set_ylim(0, y_max)

        plt.tight_layout()

        if filename is None:
            filename = "yearly_mean_comparison_bar.png"

        output_path = output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def create_yearly_coverage_comparison_bar_chart(
        self,
        results_list: List[Dict[str, Any]],
        filename: Optional[str] = None,
        sort_by: str = "sdg"
    ) -> Path:
        """
        Create a bar chart comparing mean coverage % per SDG across years.

        Similar to create_coverage_comparison_chart() but shows yearly averages
        grouped by SDG, with bars for each year side-by-side.

        Args:
            results_list: List of alignment results from multiple reports/years
            filename: Output filename (optional)
            sort_by: "coverage" to sort by average coverage, "sdg" for SDG number

        Returns:
            Path to saved figure
        """
        if not results_list:
            raise ValueError("Need at least 1 report to create chart")

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        output_dir = getattr(self, 'output_dir', Path('.'))
        _calculate_y_axis_limit = getattr(self, '_calculate_y_axis_limit', lambda x, y: max(x) * 1.1 if x else 1.0)

        # Group results by year
        from collections import defaultdict
        year_results = defaultdict(list)
        for result in results_list:
            year = result.get("metadata", {}).get("year", "Unknown")
            year_results[year].append(result)

        if len(year_results) < 1:
            raise ValueError("No valid years found in results")

        sorted_years = sorted(year_results.keys())
        sdg_nums = list(range(1, 18))
        sdg_names = [f"SDG {i}\n{sdg_reference.get_sdg_name(i)[:15]}" for i in sdg_nums]
        sdg_colors = [sdg_reference.get_sdg_color(i) for i in sdg_nums]

        # Calculate mean coverage per SDG per year
        yearly_coverage = {}
        for year in sorted_years:
            yearly_coverage[year] = {}
            for sdg_num in sdg_nums:
                coverages = []
                for result in year_results[year]:
                    report = result.get("report_alignment", {})
                    coverage_dict = report.get("coverage", {})
                    cov = coverage_dict.get(sdg_num, coverage_dict.get(str(sdg_num), 0.0))
                    coverages.append(cov * 100)  # Convert to percentage
                yearly_coverage[year][sdg_num] = np.mean(coverages) if coverages else 0.0

        # Calculate overall mean coverage per SDG for sorting
        sdg_coverage_means = {sdg_num: np.mean([yearly_coverage[year][sdg_num] for year in sorted_years])
                              for sdg_num in sdg_nums}

        # Determine sort order
        if sort_by == "coverage":
            sorted_sdgs = sorted(sdg_nums, key=lambda x: sdg_coverage_means[x], reverse=True)
        else:
            sorted_sdgs = sdg_nums

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 8))

        x = np.arange(len(sorted_sdgs))
        width = 0.8 / len(sorted_years)

        # Define colors for years
        year_colors = plt.cm.plasma(np.linspace(0, 1, len(sorted_years)))

        # Create bars for each year
        for i, year in enumerate(sorted_years):
            coverages = [yearly_coverage[year][sdg_num] for sdg_num in sorted_sdgs]
            offset = width * (i - len(sorted_years) / 2 + 0.5)
            bars = ax.bar(x + offset, coverages, width, label=f"Year {year}",
                         color=year_colors[i], alpha=0.8, edgecolor='black', linewidth=0.5)

            # Add value labels on top of bars
            for bar, cov in zip(bars, coverages):
                height = bar.get_height()
                if height > 0.5:  # Only label non-zero bars
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height + 1,
                        f'{cov:.1f}%',
                        ha='center',
                        va='bottom',
                        fontsize=6,
                        rotation=90
                    )

        ax.set_xlabel('Sustainable Development Goals', fontsize=12)
        ax.set_ylabel('Mean Coverage (% of Activities Aligned)', fontsize=12)
        ax.set_title(f'SDG Coverage by Year - Mean Coverage Comparison\n({len(sorted_years)} years)', fontsize=14, pad=20)
        ax.set_xticks(x)
        sorted_labels = [f"SDG {i}" for i in sorted_sdgs]
        ax.set_xticklabels(sorted_labels, rotation=45, ha='right')
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), framealpha=0.9)
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Set dynamic Y-axis limit
        all_coverages = [yearly_coverage[year][sdg_num] for year in sorted_years for sdg_num in sdg_nums]
        y_max = _calculate_y_axis_limit(all_coverages, is_percentage=True)
        ax.set_ylim(0, y_max)

        plt.tight_layout()

        if filename is None:
            filename = "yearly_coverage_comparison_bar.png"

        output_path = output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def create_council_coverage_chart(
        self,
        results_list: List[Dict[str, Any]],
        threshold: float,
        filename: Optional[str] = None,
        sort_by: str = "sdg",
        mode: str = "hybrid"
    ) -> Path:
        """
        Create a bar chart showing council coverage: % of councils with at least one
        activity in each SDG with score > SDG-specific threshold.

        Calculation method:
        1. For each council, collect all activity scores for each SDG
        2. Count activities with score > SDG-specific threshold (from threshold_config.py)
        3. If count > 0, council counts as having coverage for that SDG
        4. Calculate percentage: (councils with coverage / total councils) * 100

        Uses SDG-specific thresholds from threshold_config.py based on the mode parameter.

        Args:
            results_list: List of alignment results from multiple reports/years
            filename: Output filename (optional)
            sort_by: "coverage" to sort by average coverage, "sdg" for SDG number
            threshold: Base threshold (not used directly, kept for compatibility)
            mode: "hybrid", "sentence_transformer", or "sdgbert" - selects threshold config

        Returns:
            Path to saved figure
        """
        if not results_list:
            raise ValueError("Need at least 1 report to create chart")

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        output_dir = getattr(self, 'output_dir', Path('.'))

        # Group results by Urban/Rural classification
        urban_results = []
        rural_results = []
        unknown_results = []

        for result in results_list:
            urban_rural = result.get("metadata", {}).get("urban_rural", "Unknown")
            if urban_rural == "Urban":
                urban_results.append(result)
            elif urban_rural == "Rural":
                rural_results.append(result)
            else:
                unknown_results.append(result)

        has_urban_rural = len(urban_results) > 0 and len(rural_results) > 0

        # Get SDG-specific thresholds directly from the results
        # This ensures we use exactly the same thresholds that were used during analysis
        sdg_specific = {}
        default_threshold = threshold

        if results_list:
            first_result = results_list[0]
            alignment_config = first_result.get("alignment_config", {})
            # Use the exact thresholds stored in the results
            sdg_specific = alignment_config.get("sdg_specific_thresholds", {})
            default_threshold = alignment_config.get("similarity_threshold", threshold)

        def get_threshold_for_sdg(sdg_num):
            """Get the appropriate threshold for a specific SDG."""
            return sdg_specific.get(sdg_num, default_threshold)

        # Helper function to compute council coverage for a group
        def compute_coverage(group_results):
            """Compute council coverage for a group of results."""
            sdg_council_map = {sdg_num: set() for sdg_num in range(1, 18)}

            for result in group_results:
                source = result.get("source", "Unknown")
                council_name = Path(source).stem
                activities = result.get("activities", [])

                # Check each SDG independently
                for sdg_num in range(1, 18):
                    threshold_for_sdg = get_threshold_for_sdg(sdg_num)

                    # Step 2: Count activities with score > SDG-specific threshold
                    activities_above_threshold = 0
                    for activity in activities:
                        sdg_scores = activity.get("sdg_scores", {})
                        sdg_data = sdg_scores.get(str(sdg_num), {})
                        if sdg_data:
                            score = sdg_data.get("score", 0)
                            if score > threshold_for_sdg:
                                activities_above_threshold += 1

                    # Step 3: If at least one activity has score > threshold, count this council
                    if activities_above_threshold > 0:
                        sdg_council_map[sdg_num].add(council_name)

            total = len(group_results)
            if total == 0:
                return {sdg_num: 0.0 for sdg_num in range(1, 18)}, 0

            coverage = {
                sdg_num: (len(sdg_council_map[sdg_num]) / total * 100)
                for sdg_num in range(1, 18)
            }
            return coverage, total

        sdg_nums = list(range(1, 18))

        if has_urban_rural:
            # Compute coverage for Urban and Rural separately
            urban_coverage, urban_total = compute_coverage(urban_results)
            rural_coverage, rural_total = compute_coverage(rural_results)

            # Calculate mean coverage per SDG for sorting
            sdg_coverage_means = {}
            for sdg_num in sdg_nums:
                sdg_coverage_means[sdg_num] = (urban_coverage[sdg_num] + rural_coverage[sdg_num]) / 2

            # Determine sort order
            if sort_by == "coverage":
                sorted_sdgs = sorted(sdg_nums, key=lambda x: sdg_coverage_means[x], reverse=True)
            else:
                sorted_sdgs = sdg_nums

            # Create figure with Urban/Rural bars
            fig, ax = plt.subplots(figsize=(16, 8))
            x = np.arange(len(sorted_sdgs))
            width = 0.35

            # Get SDG colors
            bar_colors = [sdg_reference.get_sdg_color(i) for i in sorted_sdgs]

            # Create grouped bars
            urban_values = [urban_coverage[sdg_num] for sdg_num in sorted_sdgs]
            rural_values = [rural_coverage[sdg_num] for sdg_num in sorted_sdgs]

            bars1 = ax.bar(x - width/2, urban_values, width, label=f'Urban (n={urban_total})',
                          color=bar_colors, alpha=0.9, edgecolor='black', linewidth=0.5)
            bars2 = ax.bar(x + width/2, rural_values, width, label=f'Rural (n={rural_total})',
                          color=bar_colors, alpha=0.6, edgecolor='black', linewidth=0.5, hatch='//')

            # Add value labels
            for bar, cov in zip(bars1, urban_values):
                height = bar.get_height()
                if height > 5:
                    ax.text(bar.get_x() + bar.get_width() / 2, height + 2,
                           f'{cov:.0f}%', ha='center', va='bottom', fontsize=7)
            for bar, cov in zip(bars2, rural_values):
                height = bar.get_height()
                if height > 5:
                    ax.text(bar.get_x() + bar.get_width() / 2, height + 2,
                           f'{cov:.0f}%', ha='center', va='bottom', fontsize=7)

            # Move legend outside the plot to avoid overlap
            ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), title='Council Type', framealpha=0.9)
            title_text = f'SDG Council Coverage: Urban vs Rural\n(% with avg score > {threshold})'

            ax.set_xlabel('Sustainable Development Goals', fontsize=12)
            ax.set_ylabel('Council Coverage (% of Councils)', fontsize=12)
            ax.set_title(title_text, fontsize=14, pad=20)
            ax.set_xticks(x)
            ax.set_xticklabels([f"SDG {i}" for i in sorted_sdgs], rotation=45, ha='right')
            ax.yaxis.grid(True, linestyle='--', alpha=0.7)
            ax.set_ylim(0, 100)

            plt.tight_layout()
            plt.subplots_adjust(right=0.85)  # Make room for legend

            if filename is None:
                filename = "council_coverage_comparison_bar.png"

            output_path = output_dir / filename
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            return output_path

        # Fall back to original year-based grouping if no Urban/Rural data
        from collections import defaultdict
        year_groups = defaultdict(list)
        for result in results_list:
            year = result.get("metadata", {}).get("year", "Unknown")
            year_groups[year].append(result)

        council_coverage = {}
        for year, year_results in year_groups.items():
            if year == "Unknown":
                continue
            total_councils = len(year_results)
            if total_councils == 0:
                continue

            coverage, _ = compute_coverage(year_results)

            council_coverage[year] = {
                "total_councils": total_councils,
                "council_coverage": coverage
            }

        if not council_coverage:
            raise ValueError("No valid years found in results")

        sorted_years = sorted(council_coverage.keys())

        # Calculate overall mean coverage per SDG for sorting
        sdg_coverage_means = {}
        for sdg_num in sdg_nums:
            coverages = [council_coverage[year]["council_coverage"][sdg_num] for year in sorted_years]
            sdg_coverage_means[sdg_num] = np.mean(coverages) if coverages else 0.0

        # Determine sort order
        if sort_by == "coverage":
            sorted_sdgs = sorted(sdg_nums, key=lambda x: sdg_coverage_means[x], reverse=True)
        else:
            sorted_sdgs = sdg_nums

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 8))

        x = np.arange(len(sorted_sdgs))
        width = 0.8 / len(sorted_years)

        # Define colors for years
        year_colors = plt.cm.plasma(np.linspace(0, 1, len(sorted_years)))

        # Create bars for each year
        for i, year in enumerate(sorted_years):
            coverages = [council_coverage[year]["council_coverage"][sdg_num] for sdg_num in sorted_sdgs]
            total_councils = council_coverage[year]["total_councils"]
            offset = width * (i - len(sorted_years) / 2 + 0.5)
            bars = ax.bar(x + offset, coverages, width, label=f"Year {year} (n={total_councils})",
                         color=year_colors[i], alpha=0.8, edgecolor='black', linewidth=0.5)

            # Add value labels on top of bars
            for bar, cov in zip(bars, coverages):
                height = bar.get_height()
                if height > 5:  # Only label bars with significant coverage
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height + 2,
                        f'{cov:.0f}%',
                        ha='center',
                        va='bottom',
                        fontsize=7,
                        fontweight='bold'
                    )

        ax.set_xlabel('Sustainable Development Goals', fontsize=12)
        ax.set_ylabel('Council Coverage (% of Councils with Activities)', fontsize=12)
        ax.set_title(f'SDG Council Coverage by Year\n(% of Councils with avg score > {threshold} per SDG)', fontsize=14, pad=20)
        ax.set_xticks(x)
        sorted_labels = [f"SDG {i}\n{sdg_reference.get_sdg_name(i)[:15]}" for i in sorted_sdgs]
        ax.set_xticklabels(sorted_labels, rotation=45, ha='right', fontsize=9)
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), title='Year', framealpha=0.9)
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Set Y-axis limit (0-100 for percentages)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.subplots_adjust(right=0.85)

        if filename is None:
            filename = "council_coverage_chart.png"

        output_path = output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def create_council_coverage_line_chart(
        self,
        results_list: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Path:
        """
        Create a line chart showing council coverage trends over time.

        For each SDG, shows a line representing the percentage of councils
        with activities in that SDG across years.

        Args:
            results_list: List of alignment results from multiple reports/years
            filename: Output filename (optional)

        Returns:
            Path to saved figure
        """
        if not results_list:
            raise ValueError("Need at least 1 report to create chart")

        sdg_reference = getattr(self, 'sdg_reference', SDGReference())
        output_dir = getattr(self, 'output_dir', Path('.'))

        # Compute council coverage directly (inline to avoid mixin dependency issues)
        from collections import defaultdict
        year_groups = defaultdict(list)
        for result in results_list:
            year = result.get("metadata", {}).get("year", "Unknown")
            year_groups[year].append(result)

        council_coverage = {}
        for year, year_results in year_groups.items():
            if year == "Unknown":
                continue
            total_councils = len(year_results)
            if total_councils == 0:
                continue

            sdg_council_map = {sdg_num: set() for sdg_num in range(1, 18)}
            for result in year_results:
                source = result.get("source", "Unknown")
                council_name = Path(source).stem
                activities = result.get("activities", [])
                for activity in activities:
                    sdg_scores = activity.get("sdg_scores", {})
                    for sdg_num in range(1, 18):
                        sdg_data = sdg_scores.get(sdg_num, {})
                        if sdg_data.get("is_aligned", False):
                            sdg_council_map[sdg_num].add(council_name)

            council_coverage[year] = {
                "total_councils": total_councils,
                "council_coverage": {
                    sdg_num: (len(sdg_council_map[sdg_num]) / total_councils * 100)
                    for sdg_num in range(1, 18)
                }
            }

        if not council_coverage:
            raise ValueError("No valid years found in results")

        sorted_years = sorted(council_coverage.keys())
        sdg_nums = list(range(1, 18))

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot a line for each SDG
        for sdg_num in sdg_nums:
            coverages = [council_coverage[year]["council_coverage"][sdg_num] for year in sorted_years]
            color = sdg_reference.get_sdg_color(sdg_num)
            label = f"SDG {sdg_num}"
            ax.plot(sorted_years, coverages, marker='o', linewidth=2,
                   label=label, color=color, markersize=6)

        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Council Coverage (% of Councils)', fontsize=12)
        ax.set_title('SDG Council Coverage Trends Over Time\n(% of Councils with Activities per SDG)', fontsize=14, pad=20)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1, fontsize=8)
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_ylim(0, 100)

        plt.tight_layout()

        if filename is None:
            filename = "council_coverage_trends.png"

        output_path = output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path
