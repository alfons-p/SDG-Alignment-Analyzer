"""Dashboard UI components for the SDG Alignment Analyzer.

This module provides render functions for all dashboard visualizations and UI elements.
"""

from legacy.streamlit.dashboard.components.header import render_header
from legacy.streamlit.dashboard.components.landing import render_landing_page
from legacy.streamlit.dashboard.components.sidebar import render_sidebar_settings
from legacy.streamlit.dashboard.components.overview import render_overview, render_gaps
from legacy.streamlit.dashboard.components.visualizations import render_top_sdgs, render_radar_chart, render_heatmap
from legacy.streamlit.dashboard.components.tables import render_activities_table
from legacy.streamlit.dashboard.components.comparison import render_side_by_side_comparison, render_multi_report_comparison
from legacy.streamlit.dashboard.components.keywords import render_sdg_keyword_analysis
from legacy.streamlit.dashboard.components.downloads import render_download_buttons
from legacy.streamlit.dashboard.components.sdg_mentions import render_sdg_mentions_tab, render_single_report_sdg_mentions

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