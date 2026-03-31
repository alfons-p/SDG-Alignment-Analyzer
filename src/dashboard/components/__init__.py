"""Dashboard UI components for the SDG Alignment Analyzer.

This module provides render functions for all dashboard visualizations and UI elements.
"""

from src.dashboard.components.header import render_header
from src.dashboard.components.landing import render_landing_page
from src.dashboard.components.sidebar import render_sidebar_settings
from src.dashboard.components.overview import render_overview, render_gaps
from src.dashboard.components.visualizations import render_top_sdgs, render_radar_chart, render_heatmap
from src.dashboard.components.tables import render_activities_table
from src.dashboard.components.comparison import render_side_by_side_comparison, render_multi_report_comparison
from src.dashboard.components.keywords import render_sdg_keyword_analysis
from src.dashboard.components.downloads import render_download_buttons
from src.dashboard.components.sdg_mentions import render_sdg_mentions_tab, render_single_report_sdg_mentions

__all__ = [
    'render_header',
    'render_landing_page',
    'render_sidebar_settings',
    'render_overview',
    'render_gaps',
    'render_top_sdgs',
    'render_radar_chart',
    'render_heatmap',
    'render_activities_table',
    'render_side_by_side_comparison',
    'render_multi_report_comparison',
    'render_sdg_keyword_analysis',
    'render_download_buttons',
    'render_sdg_mentions_tab',
    'render_single_report_sdg_mentions',
]