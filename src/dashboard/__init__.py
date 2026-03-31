"""Streamlit Dashboard Module for SDG Alignment Analyzer.

Modular UI components and utilities for the web dashboard.
"""

# Utils
from src.dashboard.utils import (
    get_chart_theme_colors,
    get_score_color,
    extract_metadata_from_filename,
    SDG_COLORS,
    SDG_DATA,
    get_extractor,
    get_engine,
    get_hybrid_engine,
    get_reporter,
    get_trend_analyzer,
    get_sdg_reference,
)

# Session Management
from src.dashboard.session import (
    CacheKey,
    SessionManager,
    ProcessingState,
    AppState,
    get_session,
)

# Cache Management
from src.dashboard.cache_manager import CacheManager

# Styles
from src.dashboard.styles import STYLES, get_landing_page_styles

# Caching
from src.dashboard.caching import (
    get_cached_sdg_ref,
    get_cached_engine,
    get_cached_hybrid_engine,
)

# Processing
from src.dashboard.processing import (
    extract_activities_from_pdf_cached,
    align_activities_with_sdgs,
    process_pdf,
)

# UI Components
from src.dashboard.components import (
    render_landing_page,
    render_header,
    render_sidebar_settings,
    render_overview,
    render_gaps,
    render_top_sdgs,
    render_radar_chart,
    render_heatmap,
    render_activities_table,
    render_side_by_side_comparison,
    render_multi_report_comparison,
    render_sdg_keyword_analysis,
    render_download_buttons,
)

__all__ = [
    # Utils
    'get_chart_theme_colors',
    'get_score_color',
    'extract_metadata_from_filename',
    'SDG_COLORS',
    'SDG_DATA',
    'get_extractor',
    'get_engine',
    'get_hybrid_engine',
    'get_reporter',
    'get_trend_analyzer',
    'get_sdg_reference',
    # Session Management
    'CacheKey',
    'SessionManager',
    'ProcessingState',
    'AppState',
    'get_session',
    # Cache Management
    'CacheManager',
    # Styles
    'STYLES',
    'get_landing_page_styles',
    # Caching
    'get_cached_sdg_ref',
    'get_cached_engine',
    'get_cached_hybrid_engine',
    # Processing
    'extract_activities_from_pdf_cached',
    'align_activities_with_sdgs',
    'process_pdf',
    # UI Components
    'render_landing_page',
    'render_header',
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
]