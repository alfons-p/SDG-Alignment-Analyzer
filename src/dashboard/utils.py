"""Shim for src.dashboard.utils — moved to legacy, re-exported for backward compat."""

from legacy.streamlit.dashboard.utils import (
    SDG_COLORS,
    SDG_DATA,
    get_chart_theme_colors,
    get_score_color,
    get_extractor,
    get_engine,
    get_hybrid_engine,
    get_reporter,
    get_trend_analyzer,
    get_sdg_reference,
    extract_metadata_from_filename,
)
