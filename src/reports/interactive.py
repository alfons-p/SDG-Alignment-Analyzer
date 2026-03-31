"""Plotly-based interactive visualization module.

Contains interactive visualization methods using Plotly.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from src.config import Config, SDG_DEFINITIONS
from src.sdg_reference import SDGReference


class InteractiveMixin:
    """Mixin class providing Plotly interactive visualization methods.

    This class provides interactive visualization methods that can be mixed into Reporter.
    """

    def create_interactive_radar(self, results: Dict[str, Any]) -> go.Figure:
        """
        Create interactive Plotly radar chart.

        Args:
            results: Alignment results

        Returns:
            Plotly figure
        """
        report = results.get("report_alignment", {})
        mean_scores = report.get("mean_scores", {})

        categories = [f"SDG {i}" for i in range(1, 18)]
        values = [mean_scores.get(i, 0) for i in range(1, 18)]

        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Alignment Score'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values) * 1.1]
                )
            ),
            showlegend=False,
            title=f"SDG Alignment Profile - {Path(results.get('source', 'Report')).name}"
        )

        return fig

    def create_interactive_heatmap(self, results: Dict[str, Any]) -> go.Figure:
        """
        Create interactive Plotly heatmap.

        Args:
            results: Alignment results

        Returns:
            Plotly figure
        """
        activities = results.get("activities", [])
        if not activities:
            raise ValueError("No activities in results")

        # Take top 30 activities by relevance
        sorted_activities = sorted(
            activities,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )[:30]

        # Build matrix
        z = []
        y_labels = []

        for activity in sorted_activities:
            y_labels.append(activity["activity_text"][:40] + "...")
            sdg_scores = activity["sdg_scores"]
            row = [sdg_scores.get(i, sdg_scores.get(str(i), {})).get("score", 0) for i in range(1, 18)]
            z.append(row)

        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=[f"SDG {i}" for i in range(1, 18)],
            y=y_labels,
            colorscale='YlOrRd',
            zmin=0,
            zmax=1
        ))

        fig.update_layout(
            title=f"Activity-SDG Alignment Heatmap - {Path(results.get('source', 'Report')).name}",
            xaxis_title="Sustainable Development Goals",
            yaxis_title="Activities",
            height=800
        )

        return fig
