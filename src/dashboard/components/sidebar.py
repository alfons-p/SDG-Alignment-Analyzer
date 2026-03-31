"""Sidebar settings component for the dashboard."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

import streamlit as st

# Model paths - using Hugging Face Hub for hosted deployment
# Local path for development: models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509
MODEL_PATHS = {
    "default": "all-mpnet-base-v2",
    "fast": "all-MiniLM-L6-v2",
    "finetuned": "voyager205/sdg-finetuned-enhanced",
}

# SDG names for display
SDG_NAMES = {
    1: "No Poverty", 2: "Zero Hunger", 3: "Good Health", 4: "Quality Education",
    5: "Gender Equality", 6: "Clean Water", 7: "Affordable Energy",
    8: "Decent Work", 9: "Innovation", 10: "Reduced Inequalities",
    11: "Sustainable Cities", 12: "Responsible Consumption", 13: "Climate Action",
    14: "Life Below Water", 15: "Life on Land", 16: "Peace & Justice",
    17: "Partnerships"
}

def get_default_thresholds(mode: str) -> dict:
    """Get default thresholds from threshold_config.py (single source of truth).

    Args:
        mode: 'sentence_transformer' or 'hybrid'

    Returns:
        Dict with 'default' and 'sdg_specific' thresholds
    """
    from src.config.threshold_config import get_threshold, get_all_thresholds
    return {
        "default": get_threshold(mode),
        "sdg_specific": get_all_thresholds(mode)
    }

# Default processing parameters
DEFAULT_MIN_WORDS = 20
DEFAULT_MAX_WORDS = 500
DEFAULT_TOP_ACTIVITIES = 0


@dataclass
class ProcessingSettings:
    """Typed container for all processing settings."""
    uploaded_files: List[Any] = field(default_factory=list)
    model_name: str = MODEL_PATHS["finetuned"]
    similarity_threshold: float = 0.5
    use_hybrid: bool = False
    ensemble_mode: str = "weighted"
    sdg_bert_weight: float = 0.55
    st_weight: float = 0.45
    min_words: int = DEFAULT_MIN_WORDS
    max_words: int = DEFAULT_MAX_WORDS
    top_activities: int = DEFAULT_TOP_ACTIVITIES
    enable_sdg17_correction: bool = True
    enable_sdg11_correction: bool = True
    use_custom_thresholds: bool = False
    sdg_thresholds: Dict[int, float] = field(default_factory=dict)
    unit: str = "sentence"


# Professional balanced color palette (matches styles.py design tokens)
THEME = {
    "primary": "#c92a2a",      # Refined red (less aggressive)
    "primary_light": "#e03e3e",
    "primary_dark": "#a61e1e",
    "accent": "#c92a2a",
    "accent_hover": "#b32424",
    "success": "#10b981",
    "warning": "#f59e0b",
    "text": "#1e293b",        # Slate 800
    "text_light": "#64748b",   # Slate 500
    "border": "#e2e8f0",      # Slate 200
    "background": "#f8fafc",  # Slate 50
}


def render_sidebar_settings() -> ProcessingSettings:
    """Render the upload and settings in the left sidebar.

    Returns:
        ProcessingSettings dataclass with all configuration values.
    """
    # Add custom sidebar styling with professional theme
    st.sidebar.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            background: var(--bg-secondary, #f8fafc);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: var(--space-md, 1rem);
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--text-primary, #1e293b) !important;
        }
        section[data-testid="stSidebar"] .stExpander {
            border: 1px solid var(--border-light, #e2e8f0);
            border-radius: var(--radius-md, 0.75rem);
        }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar header with branding
    st.sidebar.markdown(f"""
    <div style="text-align: center; padding: var(--space-md, 1rem) 0; margin-bottom: var(--space-md, 1rem); border-bottom: 1px solid var(--border-light, #e2e8f0);">
        <h2 style="margin: 0; color: {THEME['primary']}; font-weight: var(--font-extrabold, 800); font-size: var(--text-2xl, 1.5rem);">SDG Analyzer</h2>
        <p style="margin: 0.25rem 0 0 0; color: var(--text-secondary, #64748b); font-size: var(--text-xs, 0.75rem);">Local Government AI Platform</p>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.header("📁 Reports")

    uploaded_files = st.sidebar.file_uploader(
        "Upload PDF annual report(s)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more council annual reports in PDF format"
    )

    st.sidebar.markdown("---")

    # Model Settings
    with st.sidebar.expander("🤖 Model Settings", expanded=True):
        model_options = {
            MODEL_PATHS["default"]: "all-mpnet-base-v2 (Default)",
            MODEL_PATHS["fast"]: "all-MiniLM-L6-v2 (Fast)",
            MODEL_PATHS["finetuned"]: "Fine-tuned Enhanced"
        }
        model_choice = st.selectbox(
            "Embedding Model",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            index=2,
            help="Fine-tuned Enhanced is recommended for best accuracy."
        )

        use_hybrid = st.toggle(
            "Use Hybrid Ensemble",
            value=False,
            help="Combines sdgBERT + ST for 90-92% accuracy (slower initial load)"
        )

        if use_hybrid:
            ensemble_mode = st.selectbox(
                "Ensemble Mode",
                ["weighted", "fallback", "single"],
                index=0,
                help="weighted: Combine scores, fallback: Use sdgBERT when ST uncertain"
            )

            sdg_bert_weight = st.slider(
                "sdgBERT Weight",
                min_value=0.0,
                max_value=1.0,
                value=0.55,
                step=0.05,
                help="Weight for sdgBERT in ensemble"
            )
            st_weight = 1.0 - sdg_bert_weight
            st.caption(f"ST Weight: {st_weight:.2f}")
            default_threshold = 0.5
        else:
            ensemble_mode = "weighted"
            sdg_bert_weight = 0.55
            st_weight = 0.45
            default_threshold = 0.5

    # Threshold Settings - Simplified with presets
    mode = "hybrid" if use_hybrid else "sentence_transformer"
    defaults = get_default_thresholds(mode)

    # Initialize session state for thresholds if not exists
    if f"threshold_preset_{mode}" not in st.session_state:
        st.session_state[f"threshold_preset_{mode}"] = "default"
    if f"custom_thresholds_{mode}" not in st.session_state:
        st.session_state[f"custom_thresholds_{mode}"] = defaults["sdg_specific"].copy()

    with st.sidebar.expander("📏 Threshold Settings", expanded=False):
        # Preset selector - much simpler than 17 sliders
        threshold_preset = st.selectbox(
            "Threshold Preset",
            options=["default", "strict", "lenient", "custom"],
            index=["default", "strict", "lenient", "custom"].index(st.session_state.get(f"threshold_preset_{mode}", "default")),
            help="Choose a preset or select 'custom' for fine-tuned control"
        )
        st.session_state[f"threshold_preset_{mode}"] = threshold_preset

        # Apply preset logic
        if threshold_preset == "strict":
            # Higher thresholds - fewer but stronger alignments
            multiplier = 1.2
            sdg_thresholds = {sdg: min(1.0, thresh * multiplier) for sdg, thresh in defaults["sdg_specific"].items()}
            similarity_threshold = min(1.0, default_threshold * multiplier)
        elif threshold_preset == "lenient":
            # Lower thresholds - more inclusive alignments
            multiplier = 0.8
            sdg_thresholds = {sdg: max(0.1, thresh * multiplier) for sdg, thresh in defaults["sdg_specific"].items()}
            similarity_threshold = max(0.1, default_threshold * multiplier)
        elif threshold_preset == "custom":
            # Show single global threshold slider (not 17 individual ones)
            similarity_threshold = st.slider(
                "Global Threshold",
                min_value=0.0,
                max_value=1.0,
                value=default_threshold,
                step=0.05,
                help="Applies to all SDGs uniformly"
            )
            sdg_thresholds = defaults["sdg_specific"].copy()
            st.caption("💡 For per-SDG thresholds, see Advanced Settings below")
        else:  # default
            sdg_thresholds = defaults["sdg_specific"].copy()
            similarity_threshold = default_threshold

        # Show preset info
        if threshold_preset == "strict":
            st.info("Strict: Higher thresholds = fewer but stronger alignments")
        elif threshold_preset == "lenient":
            st.info("Lenient: Lower thresholds = more inclusive alignments")
        else:
            st.info(f"Default: {default_threshold:.2f} for all SDGs")

    # Bias Correction Settings
    with st.sidebar.expander("🔧 Bias Corrections"):
        st.caption("Post-processing corrections for known classification biases")

        enable_sdg17_correction = st.toggle(
            "SDG 17 Bias Correction",
            value=True,
            help="Reduce false positives from local governance keywords"
        )

        enable_sdg11_correction = st.toggle(
            "SDG 11 Bias Correction",
            value=True,
            help="Demote generic community activities without sustainability terms"
        )

    # Activity filtering
    with st.sidebar.expander("🔍 Activity Filters"):
        unit = st.radio(
            "Activity Unit",
            options=["sentence", "paragraph"],
            format_func=lambda x: "Sentence" if x == "sentence" else "Paragraph",
            help="Unit of analysis. 'Sentence' treats each sentence as a potential activity. 'Paragraph' treats each paragraph as a potential activity.",
            horizontal=True,
            index=0
        )

        min_words = st.number_input(
            "Min Words",
            min_value=5,
            max_value=100,
            value=DEFAULT_MIN_WORDS,
            help="Minimum word count for activities"
        )
        max_words = st.number_input(
            "Max Words",
            min_value=50,
            max_value=1000,
            value=DEFAULT_MAX_WORDS,
            help="Maximum word count for activities"
        )
        top_activities = st.number_input(
            "Top N Activities (0=all)",
            min_value=0,
            max_value=10000,
            value=DEFAULT_TOP_ACTIVITIES,
            help="Limit to top N activities (0 = analyze all)"
        )

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Tools")

    if st.sidebar.button("🗑️ Clear Cache", help="Clear all cached data and models"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.sidebar.success("Cache cleared!")
        st.rerun()

    return ProcessingSettings(
        uploaded_files=uploaded_files if uploaded_files else [],
        model_name=model_choice,
        similarity_threshold=similarity_threshold,
        use_hybrid=use_hybrid,
        ensemble_mode=ensemble_mode,
        sdg_bert_weight=sdg_bert_weight,
        st_weight=st_weight,
        min_words=min_words,
        max_words=max_words,
        top_activities=top_activities,
        enable_sdg17_correction=enable_sdg17_correction,
        enable_sdg11_correction=enable_sdg11_correction,
        use_custom_thresholds=False,
        sdg_thresholds=sdg_thresholds,
        unit=unit,
    )