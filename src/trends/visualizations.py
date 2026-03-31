"""Trend visualization module.

Contains visualization methods for trend analysis using
matplotlib, seaborn, and plotly.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.trends.core import TrendResult
from src.config import SDG_DEFINITIONS


class VisualizationMixin:
    """Mixin class providing trend visualization methods."""

    def create_trend_visualization(self, trends: Dict[int, TrendResult],
                                    title: str = "SDG Trend Analysis",
                                    filename: Optional[str] = None,
                                    output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create a multi-line trend visualization.

        Args:
            trends: Dictionary mapping SDG number to TrendResult
            title: Plot title
            filename: Output filename (optional)
            output_dir: Output directory (optional)

        Returns:
            Path to saved figure, or None if no trends
        """
        if not trends:
            print("No trends to visualize")
            return None

        results_dir = getattr(self, 'results_dir', Path('.'))
        output_dir = output_dir or results_dir / "trends"
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = "trend_analysis.png"

        output_path = output_dir / filename

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot each SDG trend
        for sdg_num, trend in sorted(trends.items()):
            color = SDG_DEFINITIONS.get(sdg_num, {}).get('color', '#333333')

            # Determine line style based on significance
            linestyle = '-' if trend.is_significant else '--'
            linewidth = 2.5 if trend.is_significant else 1.5

            ax.plot(trend.years, trend.scores, label=f"SDG {sdg_num}: {trend.sdg_name}",
                   color=color, linestyle=linestyle, linewidth=linewidth, marker='o', markersize=6)

        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Mean Alignment Score', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 1)

        plt.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path

    def create_trend_heatmap(self, trends: Dict[int, TrendResult],
                              title: str = "SDG Trend Direction Heatmap",
                              filename: Optional[str] = None,
                              output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create a heatmap showing trend directions and magnitudes.

        Args:
            trends: Dictionary mapping SDG number to TrendResult
            title: Plot title
            filename: Output filename (optional)
            output_dir: Output directory (optional)

        Returns:
            Path to saved figure, or None if no trends
        """
        if not trends:
            print("No trends to visualize")
            return None

        results_dir = getattr(self, 'results_dir', Path('.'))
        output_dir = output_dir or results_dir / "trends"
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = "trend_heatmap.png"

        output_path = output_dir / filename

        # Prepare data for heatmap
        sdg_nums = sorted(trends.keys())
        sdg_names = [f"{n}: {trends[n].sdg_name[:20]}" for n in sdg_nums]

        # Create metrics
        slopes = [trends[n].trend_slope for n in sdg_nums]
        r_squared = [trends[n].r_squared for n in sdg_nums]
        percent_changes = [trends[n].percent_change for n in sdg_nums]

        # Create DataFrame
        data = {
            'Slope': slopes,
            'R-squared': r_squared,
            'Percent Change (%)': percent_changes
        }
        df = pd.DataFrame(data, index=sdg_names)

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 12))

        # Create heatmap
        sns.heatmap(df, annot=True, fmt='.3f', cmap='RdYlGn', center=0,
                   cbar_kws={'label': 'Value'}, ax=ax, linewidths=0.5)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Metric', fontsize=12)
        ax.set_ylabel('SDG', fontsize=12)

        plt.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path

    def create_trend_bar_chart(self, trends: Dict[int, TrendResult],
                                title: str = "SDG Trend Analysis Summary",
                                filename: Optional[str] = None,
                                output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create a bar chart showing trend slopes with significance indicators.

        Args:
            trends: Dictionary mapping SDG number to TrendResult
            title: Plot title
            filename: Output filename (optional)
            output_dir: Output directory (optional)

        Returns:
            Path to saved figure, or None if no trends
        """
        if not trends:
            print("No trends to visualize")
            return None

        results_dir = getattr(self, 'results_dir', Path('.'))
        output_dir = output_dir or results_dir / "trends"
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = "trend_bar_chart.png"

        output_path = output_dir / filename

        # Prepare data
        sdg_nums = sorted(trends.keys())
        sdg_labels = [f"SDG {n}" for n in sdg_nums]
        slopes = [trends[n].trend_slope for n in sdg_nums]
        colors = [SDG_DEFINITIONS.get(n, {}).get('color', '#333333') for n in sdg_nums]

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))

        bars = ax.bar(sdg_labels, slopes, color=colors, edgecolor='black', linewidth=0.5)

        # Add significance indicators
        for i, n in enumerate(sdg_nums):
            if trends[n].is_significant:
                ax.text(i, slopes[i], '*', ha='center', va='bottom',
                       fontsize=16, color='black', fontweight='bold')

        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax.set_xlabel('SDG', fontsize=12)
        ax.set_ylabel('Trend Slope', fontsize=12)
        ax.set_title(f"{title}\n(* indicates statistically significant trend, p < 0.05)",
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path

    def create_interactive_trend_plot(self, trends: Dict[int, TrendResult],
                                       title: str = "SDG Trend Analysis") -> Optional[go.Figure]:
        """
        Create an interactive Plotly trend visualization.

        Args:
            trends: Dictionary mapping SDG number to TrendResult
            title: Plot title

        Returns:
            Plotly Figure object, or None if no trends
        """
        if not trends:
            return None

        fig = go.Figure()

        for sdg_num, trend in sorted(trends.items()):
            color = SDG_DEFINITIONS.get(sdg_num, {}).get('color', '#333333')

            # Add trace
            fig.add_trace(go.Scatter(
                x=trend.years,
                y=trend.scores,
                mode='lines+markers',
                name=f"SDG {sdg_num}: {trend.sdg_name}",
                line=dict(color=color, width=2),
                marker=dict(size=8),
                hovertemplate=f"<b>SDG {sdg_num}: {trend.sdg_name}</b><br>" +
                             "Year: %{x}<br>" +
                             "Score: %{y:.3f}<br>" +
                             f"Trend: {trend.trend_direction}<br>" +
                             f"Slope: {trend.trend_slope:.4f}<br>" +
                             f"R²: {trend.r_squared:.3f}<extra></extra>"
            ))

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="Year",
            yaxis_title="Mean Alignment Score",
            yaxis_range=[0, 1],
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            margin=dict(r=150)
        )

        return fig

    def create_multi_council_trend_plot(self, council_trends: Dict[str, Dict[int, TrendResult]],
                                       sdg_num: int,
                                       title: Optional[str] = None) -> go.Figure:
        """
        Create an interactive plot comparing trends across multiple councils for a specific SDG.

        Args:
            council_trends: Dictionary mapping council name to trends dictionary
            sdg_num: SDG number to visualize
            title: Plot title (optional)

        Returns:
            Plotly Figure object
        """
        fig = go.Figure()

        sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get('name', f'SDG {sdg_num}')
        color = SDG_DEFINITIONS.get(sdg_num, {}).get('color', '#333333')

        if title is None:
            title = f"{sdg_name} Trends Across Councils"

        for council_name, trends in council_trends.items():
            if sdg_num in trends:
                trend = trends[sdg_num]
                fig.add_trace(go.Scatter(
                    x=trend.years,
                    y=trend.scores,
                    mode='lines+markers',
                    name=council_name,
                    marker=dict(size=8),
                    hovertemplate=f"<b>{council_name}</b><br>" +
                                 "Year: %{x}<br>" +
                                 "Score: %{y:.3f}<extra></extra>"
                ))

        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis_title="Year",
            yaxis_title="Mean Alignment Score",
            yaxis_range=[0, 1],
            hovermode='x unified'
        )

        return fig
