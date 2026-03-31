"""Dashboard utility functions and constants."""

from typing import Dict, Any
import streamlit as st


# SDG Colors
SDG_COLORS = {
    1: "#E5243B", 2: "#DDA63A", 3: "#4C9F38", 4: "#C5192D",
    5: "#FF3A21", 6: "#26BDE2", 7: "#FCC30B", 8: "#A21942",
    9: "#FD6925", 10: "#DD1367", 11: "#FD9D24", 12: "#BF8B2E",
    13: "#3F7E44", 14: "#0A97D9", 15: "#56C02B", 16: "#00689D",
    17: "#19486A"
}


# SDG Full Names and Descriptions
SDG_DATA = {
    1: {"name": "No Poverty", "description": "End poverty in all its forms everywhere", "icon": "👥"},
    2: {"name": "Zero Hunger", "description": "End hunger, achieve food security and improved nutrition", "icon": "🌾"},
    3: {"name": "Good Health and Well-being", "description": "Ensure healthy lives and promote well-being for all", "icon": "❤️"},
    4: {"name": "Quality Education", "description": "Ensure inclusive and equitable quality education", "icon": "📚"},
    5: {"name": "Gender Equality", "description": "Achieve gender equality and empower all women and girls", "icon": "⚖️"},
    6: {"name": "Clean Water and Sanitation", "description": "Ensure availability of water and sanitation for all", "icon": "💧"},
    7: {"name": "Affordable and Clean Energy", "description": "Ensure access to affordable, reliable, sustainable energy", "icon": "⚡"},
    8: {"name": "Decent Work and Economic Growth", "description": "Promote sustained, inclusive and sustainable economic growth", "icon": "📈"},
    9: {"name": "Industry, Innovation and Infrastructure", "description": "Build resilient infrastructure and foster innovation", "icon": "🏗️"},
    10: {"name": "Reduced Inequalities", "description": "Reduce inequality within and among countries", "icon": "🤝"},
    11: {"name": "Sustainable Cities and Communities", "description": "Make cities inclusive, safe, resilient and sustainable", "icon": "🏙️"},
    12: {"name": "Responsible Consumption and Production", "description": "Ensure sustainable consumption and production patterns", "icon": "♻️"},
    13: {"name": "Climate Action", "description": "Take urgent action to combat climate change", "icon": "🌍"},
    14: {"name": "Life Below Water", "description": "Conserve and sustainably use the oceans and marine resources", "icon": "🌊"},
    15: {"name": "Life on Land", "description": "Protect, restore and promote sustainable use of terrestrial ecosystems", "icon": "🌳"},
    16: {"name": "Peace, Justice and Strong Institutions", "description": "Promote peaceful and inclusive societies", "icon": "🕊️"},
    17: {"name": "Partnerships for the Goals", "description": "Strengthen the means of implementation", "icon": "🤲"}
}


def get_chart_theme_colors():
    """Get appropriate colors based on Streamlit's theme (light/dark mode)."""
    try:
        # Get theme from Streamlit
        theme = st.get_option("theme.base")
        is_dark = theme == "dark"
    except:
        # Default to light if can't detect
        is_dark = False

    if is_dark:
        return {
            'text': '#FFFFFF',
            'text_secondary': '#CCCCCC',
            'grid': 'rgba(255, 255, 255, 0.2)',
            'background': 'rgba(30, 30, 30, 0.8)',
            'paper_bg': 'rgba(30, 30, 30, 0.3)',
            'legend_bg': 'rgba(50, 50, 50, 0.8)'
        }
    else:
        return {
            'text': '#333333',
            'text_secondary': '#666666',
            'grid': 'rgba(128, 128, 128, 0.3)',
            'background': 'rgba(255, 255, 255, 0.8)',
            'paper_bg': 'rgba(255, 255, 255, 0.3)',
            'legend_bg': 'rgba(255, 255, 255, 0.8)'
        }


def get_score_color(score: float) -> str:
    """Get color based on score."""
    if score >= 0.5:
        return "#28a745"  # Green
    elif score >= 0.3:
        return "#ffc107"  # Yellow
    else:
        return "#dc3545"  # Red


def extract_metadata_from_filename(filename: str) -> Dict[str, str]:
    """Extract year, state, council, and urban/rural classification from filename.

    Supports standardized format: {state}_{council}_{region_type}_{year}.pdf
    Falls back to pattern matching for non-standard filenames.

    Args:
        filename: The uploaded file name

    Returns:
        Dictionary with year, state, council_name, urban_rural, and source
    """
    import re

    metadata = {
        'year': '',
        'state': '',
        'council_name': '',
        'urban_rural': '',
        'source': filename
    }

    # Try to extract year (4 digits)
    year_match = re.search(r'20\d{2}', filename)
    if year_match:
        metadata['year'] = year_match.group(0)

    # Try to extract state (common abbreviations)
    state_patterns = ['VIC', 'NSW', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT']
    for state in state_patterns:
        if state in filename.upper():
            metadata['state'] = state
            break

    # Extract urban/rural from filename
    filename_lower = filename.lower()
    if 'urban' in filename_lower:
        metadata['urban_rural'] = 'Urban'
    elif 'rural' in filename_lower:
        metadata['urban_rural'] = 'Rural'

    # Try to extract council name from standardized format: {state}_{council}_{region_type}_{year}
    # Pattern: STATE_councilname_Urban/Rural_YEAR
    standardized_match = re.match(
        r'([A-Z]{2,3})_([^_]+)_(Urban|Rural|nan)_([0-9]{4})',
        filename,
        re.IGNORECASE
    )
    if standardized_match:
        metadata['state'] = standardized_match.group(1).upper()
        metadata['council_name'] = standardized_match.group(2).replace('_', ' ')
        metadata['urban_rural'] = standardized_match.group(3)
        metadata['year'] = standardized_match.group(4)

    return metadata


# Lazy imports to speed up page load
def get_extractor(min_words: int = 20, max_words: int = 500):
    from src.activity_extractor import ActivityExtractor
    return ActivityExtractor(min_activity_length=min_words, max_activity_length=max_words)


def get_engine():
    from src.alignment_engine import AlignmentEngine
    return AlignmentEngine()


def get_hybrid_engine(
    model_name: str,
    similarity_threshold: float,
    ensemble_mode: str = "weighted",
    sdg_bert_weight: float = 0.55,
    st_weight: float = 0.45,
    enable_sdg17_correction: bool = True,
    enable_sdg11_correction: bool = True,
    use_custom_thresholds: bool = False,
    custom_sdg_thresholds: dict = None
):
    """Initialize hybrid alignment engine with sdgBERT support."""
    from src.hybrid_alignment_engine import HybridAlignmentEngine
    return HybridAlignmentEngine(
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        use_sdg_bert=True,
        ensemble_mode=ensemble_mode,
        sdg_bert_weight=sdg_bert_weight,
        st_weight=st_weight,
        enable_sdg17_correction=enable_sdg17_correction,
        enable_sdg11_correction=enable_sdg11_correction,
        use_custom_thresholds=use_custom_thresholds,
        custom_sdg_thresholds=custom_sdg_thresholds
    )


def get_reporter():
    from src.reports import Reporter
    return Reporter()


def get_trend_analyzer():
    from src.trends import TrendAnalyzer
    return TrendAnalyzer()


def get_sdg_reference():
    from src.sdg_reference import SDGReference
    return SDGReference()
