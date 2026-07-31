"""Shim module — re-exports from legacy dashboard for backward compatibility.

After migration of app.py + src/dashboard/ to legacy/streamlit/,
this shim keeps existing imports working (tests, scripts).
"""

import sys
from pathlib import Path

# Add project root for legacy import
_legacy_root = Path(__file__).parent.parent.parent / "legacy" / "streamlit"
if str(_legacy_root) not in sys.path:
    sys.path.insert(0, str(_legacy_root))

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
from legacy.streamlit.dashboard.session import SessionManager, CacheKey
from legacy.streamlit.dashboard.cache_manager import CacheManager
from legacy.streamlit.dashboard.styles import get_landing_page_styles
from legacy.streamlit.dashboard.processing import process_pdf, scan_sdg_mentions_cached
