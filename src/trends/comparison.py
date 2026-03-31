"""Trend comparison module.

Contains methods for comparing trends across multiple councils
and states.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import matplotlib.pyplot as plt
import numpy as np

from src.trends.core import TrendResult
from src.trends.analysis import AnalysisMixin
from src.trends.visualizations import VisualizationMixin
from src.config import SDG_DEFINITIONS


class ComparisonMixin(AnalysisMixin, VisualizationMixin):
    """Mixin class providing trend comparison methods.

    Inherits from AnalysisMixin and VisualizationMixin to provide
    access to analysis and visualization methods.
    """

    def create_council_comparison_trends(self, council_names: List[str]) -> Dict[str, Dict[int, TrendResult]]:
        """
        Analyze trends for multiple councils and return combined results.

        Args:
            council_names: List of council names to compare

        Returns:
            Dictionary mapping council name to its trends dictionary
        """
        all_trends = {}
        for council in council_names:
            trends = self.analyze_council_trends(council)
            if trends:
                all_trends[council] = trends

        return all_trends

    def create_state_comparison_visualization(self, state_trends: Dict[str, Dict[int, TrendResult]],
                                               title: str = "State Comparison: SDG Trends",
                                               filename: Optional[str] = None,
                                               output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create a visualization comparing trends across states.

        Args:
            state_trends: Dictionary mapping state to trends dictionary
            title: Plot title
            filename: Output filename (optional)
            output_dir: Output directory (optional)

        Returns:
            Path to saved figure, or None if no trends
        """
        if not state_trends:
            print("No state trends to visualize")
            return None

        results_dir = getattr(self, 'results_dir', Path('.'))
        output_dir = output_dir or results_dir / "trends"
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = "state_comparison_trends.png"

        output_path = output_dir / filename

        # Create subplots - one row per SDG, or grid
        n_sdgs = 17
        n_cols = 3
        n_rows = (n_sdgs + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, n_rows * 4))
        axes = axes.flatten()

        state_colors = {'NSW': '#1f77b4', 'VIC': '#ff7f0e', 'QLD': '#2ca02c',
                       'WA': '#d62728', 'SA': '#9467bd', 'TAS': '#8c564b',
                       'ACT': '#e377c2', 'NT': '#7f7f7f'}

        for sdg_num in range(1, 18):
            ax = axes[sdg_num - 1]
            sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get('name', f'SDG {sdg_num}')
            sdg_color = SDG_DEFINITIONS.get(sdg_num, {}).get('color', '#333333')

            for state, trends in state_trends.items():
                if sdg_num in trends:
                    trend = trends[sdg_num]
                    color = state_colors.get(state, '#333333')
                    ax.plot(trend.years, trend.scores, label=state,
                           color=color, marker='o', markersize=6, linewidth=2)

            ax.set_title(f"SDG {sdg_num}: {sdg_name}", fontsize=10, fontweight='bold',
                        color=sdg_color)
            ax.set_xlabel('Year', fontsize=8)
            ax.set_ylabel('Score', fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)

            if sdg_num == 1:
                ax.legend(loc='upper right', fontsize=8)

        # Hide unused subplots
        for i in range(n_sdgs, len(axes)):
            axes[i].axis('off')

        plt.suptitle(title, fontsize=16, fontweight='bold', y=1.00)
        plt.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path

    def create_state_comparison_bar_chart(self, state_trends: Dict[str, Dict[int, TrendResult]],
                                          title: str = "State Comparison: Trend Slopes",
                                          filename: Optional[str] = None,
                                          output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create a bar chart comparing trend slopes across states.

        Args:
            state_trends: Dictionary mapping state to trends dictionary
            title: Plot title
            filename: Output filename (optional)
            output_dir: Output directory (optional)

        Returns:
            Path to saved figure, or None if no trends
        """
        if not state_trends:
            print("No state trends to visualize")
            return None

        results_dir = getattr(self, 'results_dir', Path('.'))
        output_dir = output_dir or results_dir / "trends"
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = "state_comparison_slopes.png"

        output_path = output_dir / filename

        # Prepare data
        states = sorted(state_trends.keys())
        sdg_nums = list(range(1, 18))

        fig, ax = plt.subplots(figsize=(16, 8))

        x = np.arange(len(sdg_nums))
        width = 0.8 / len(states)

        state_colors = {'NSW': '#1f77b4', 'VIC': '#ff7f0e', 'QLD': '#2ca02c',
                       'WA': '#d62728', 'SA': '#9467bd', 'TAS': '#8c564b',
                       'ACT': '#e377c2', 'NT': '#7f7f7f'}

        for i, state in enumerate(states):
            slopes = []
            for sdg_num in sdg_nums:
                if sdg_num in state_trends[state]:
                    slopes.append(state_trends[state][sdg_num].trend_slope)
                else:
                    slopes.append(0)

            offset = width * (i - len(states) / 2 + 0.5)
            color = state_colors.get(state, '#333333')
            ax.bar(x + offset, slopes, width, label=state, color=color, alpha=0.8)

        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax.set_xlabel('SDG', fontsize=12)
        ax.set_ylabel('Trend Slope', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f"{i}" for i in sdg_nums])
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path
