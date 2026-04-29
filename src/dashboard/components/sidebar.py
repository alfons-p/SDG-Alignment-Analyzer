"""Sidebar settings component for the dashboard."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

import streamlit as st

# Model options
MODEL_FINETUNED = "voyager205/sdg-variant-finetuned"
MODEL_FALLBACK = "all-mpnet-base-v2"

# SDGs with bias correction modules
BIAS_CORRECTION_SDGS = [4, 6, 8, 10, 11, 12, 14, 16, 17]

# Default processing parameters
DEFAULT_MIN_WORDS = 20
DEFAULT_MAX_WORDS = 500
DEFAULT_TOP_ACTIVITIES = 0


@dataclass
class ProcessingSettings:
    """Typed container for all processing settings."""
    uploaded_files: List[Any] = field(default_factory=list)
    model_name: str = MODEL_FINETUNED
    similarity_threshold: float = 0.5
    use_hybrid: bool = True
    ensemble_mode: str = "weighted"
    min_words: int = DEFAULT_MIN_WORDS
    max_words: int = DEFAULT_MAX_WORDS
    top_activities: int = DEFAULT_TOP_ACTIVITIES
    enable_bias_corrections: bool = True
    bias_corrections: Dict[int, bool] = field(default_factory=dict)
    use_custom_thresholds: bool = False
    sdg_thresholds: Dict[int, float] = field(default_factory=dict)


THEME = {
    "primary": "#c92a2a",
    "primary_light": "#e03e3e",
    "primary_dark": "#a61e1e",
    "accent": "#c92a2a",
    "accent_hover": "#b32424",
    "success": "#10b981",
    "warning": "#f59e0b",
    "text": "#1e293b",
    "text_light": "#64748b",
    "border": "#e2e8f0",
    "background": "#f8fafc",
}


def _get_default_thresholds(mode: str) -> dict:
    """Get default thresholds from threshold_config.py."""
    from src.config.threshold_config import get_threshold, get_all_thresholds
    return {
        "default": get_threshold(mode),
        "sdg_specific": get_all_thresholds(mode)
    }


def _render_model_section() -> str:
    """Render model selection. Returns chosen model_name."""
    st.markdown("### 🤖 Model")
    model_options = {
        MODEL_FINETUNED: "Fine-tuned SDG (recommended)",
        MODEL_FALLBACK: "all-mpnet-base-v2 (offline fallback)",
    }
    return st.selectbox(
        "Embedding Model",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=0,
        help="Fine-tuned model downloads ~1GB from HuggingFace on first use."
    )


def _render_hybrid_section() -> tuple:
    """Render hybrid ensemble settings. Returns (use_hybrid, ensemble_mode)."""
    st.markdown("### ⚡ Ensemble")

    use_hybrid = st.toggle(
        "Hybrid Ensemble",
        value=True,
        help="sdgBERT + Sentence Transformer with per-SDG weights. 77% macro F1."
    )

    if use_hybrid:
        ensemble_mode = st.selectbox(
            "Ensemble Mode",
            ["weighted", "fallback", "single"],
            index=0,
            help="weighted: combine scores. fallback: sdgBERT when ST uncertain."
        )
        st.caption("Per-SDG weights loaded from ensemble config (auto-optimized).")
    else:
        ensemble_mode = "weighted"
        st.caption("Sentence Transformer only (legacy mode).")

    return use_hybrid, ensemble_mode


def _render_threshold_section(use_hybrid: bool) -> tuple:
    """Render threshold settings. Returns (similarity_threshold, sdg_thresholds)."""
    mode = "hybrid" if use_hybrid else "sentence_transformer"
    defaults = _get_default_thresholds(mode)
    default_threshold = 0.5

    if f"threshold_preset_{mode}" not in st.session_state:
        st.session_state[f"threshold_preset_{mode}"] = "default"

    with st.expander("📏 Threshold Settings", expanded=False):
        threshold_preset = st.selectbox(
            "Threshold Preset",
            options=["default", "strict", "lenient"],
            index=0,
            help="default: 0.5 | strict: fewer, stronger matches | lenient: more inclusive"
        )

        if threshold_preset == "strict":
            multiplier = 1.2
            sdg_thresholds = {sdg: min(1.0, t * multiplier) for sdg, t in defaults["sdg_specific"].items()}
            similarity_threshold = min(1.0, default_threshold * multiplier)
        elif threshold_preset == "lenient":
            multiplier = 0.8
            sdg_thresholds = {sdg: max(0.1, t * multiplier) for sdg, t in defaults["sdg_specific"].items()}
            similarity_threshold = max(0.1, default_threshold * multiplier)
        else:
            sdg_thresholds = defaults["sdg_specific"].copy()
            similarity_threshold = default_threshold

    return similarity_threshold, sdg_thresholds


def _render_bias_correction_section() -> tuple:
    """Render bias correction toggles. Returns (enable_bias_corrections, bias_corrections dict)."""
    with st.expander("🔧 Bias Corrections", expanded=False):
        enable_bias = st.toggle(
            "Enable per-SDG bias corrections",
            value=True,
            help="Post-processing corrections for known classification biases across 9 SDGs."
        )

        bias_corrections = {}
        for sdg in BIAS_CORRECTION_SDGS:
            bias_corrections[sdg] = enable_bias

        # Advanced: individual toggles
        if enable_bias:
            with st.expander("Advanced: per-SDG toggles", expanded=False):
                st.caption("Disable specific corrections if needed for debugging.")
                for sdg in BIAS_CORRECTION_SDGS:
                    bias_corrections[sdg] = st.toggle(
                        f"SDG {sdg}",
                        value=True,
                        key=f"bias_sdg_{sdg}"
                    )

    return enable_bias, bias_corrections


def _render_filter_section() -> tuple:
    """Render activity filter settings. Returns (min_words, max_words, top_activities)."""
    with st.expander("🔍 Activity Filters", expanded=False):
        min_words = st.number_input("Min Words", min_value=5, max_value=100, value=DEFAULT_MIN_WORDS)
        max_words = st.number_input("Max Words", min_value=50, max_value=1000, value=DEFAULT_MAX_WORDS)
        top_activities = st.number_input(
            "Top N Activities (0=all)", min_value=0, max_value=10000, value=DEFAULT_TOP_ACTIVITIES
        )
    return min_words, max_words, top_activities


def render_sidebar_settings() -> ProcessingSettings:
    """Render the upload and settings in the left sidebar."""
    st.sidebar.markdown(f"""
    <style>
        section[data-testid="stSidebar"] {{
            background: var(--bg-secondary, #f8fafc);
        }}
        section[data-testid="stSidebar"] .block-container {{
            padding-top: var(--space-md, 1rem);
        }}
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: var(--text-primary, #1e293b) !important;
        }}
        section[data-testid="stSidebar"] .stExpander {{
            border: 1px solid var(--border-light, #e2e8f0);
            border-radius: var(--radius-md, 0.75rem);
        }}
    </style>
    <div style="text-align: center; padding: var(--space-md, 1rem) 0; margin-bottom: var(--space-md, 1rem); border-bottom: 1px solid var(--border-light, #e2e8f0);">
        <h2 style="margin: 0; color: {THEME['primary']}; font-weight: var(--font-extrabold, 800); font-size: var(--text-2xl, 1.5rem);">SDG Analyzer</h2>
        <p style="margin: 0.25rem 0 0 0; color: var(--text-secondary, #64748b); font-size: var(--text-xs, 0.75rem);">Local Government AI Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # File upload
    st.sidebar.header("📁 Reports")
    uploaded_files = st.sidebar.file_uploader(
        "Upload PDF annual report(s)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more council annual reports in PDF format"
    )
    st.sidebar.markdown("---")

    # Model
    model_name = _render_model_section()
    st.sidebar.markdown("---")

    # Ensemble
    use_hybrid, ensemble_mode = _render_hybrid_section()

    # Threshold
    similarity_threshold, sdg_thresholds = _render_threshold_section(use_hybrid)

    # Bias corrections
    enable_bias, bias_corrections = _render_bias_correction_section()

    # Filters
    min_words, max_words, top_activities = _render_filter_section()

    st.sidebar.markdown("---")
    st.sidebar.header("🛠️ Tools")
    if st.sidebar.button("🗑️ Clear Cache", help="Clear all cached data and models"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.sidebar.success("Cache cleared!")
        st.rerun()

    return ProcessingSettings(
        uploaded_files=uploaded_files if uploaded_files else [],
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        use_hybrid=use_hybrid,
        ensemble_mode=ensemble_mode,
        min_words=min_words,
        max_words=max_words,
        top_activities=top_activities,
        enable_bias_corrections=enable_bias,
        bias_corrections=bias_corrections,
        use_custom_thresholds=False,
        sdg_thresholds=sdg_thresholds,
    )
