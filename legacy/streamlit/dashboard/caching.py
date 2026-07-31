"""Cached resource loaders for the SDG Alignment Analyzer dashboard.

This module provides Streamlit-cached versions of resource-heavy operations
like model loading and SDG reference initialization.
"""

import streamlit as st

from legacy.streamlit.dashboard.utils import get_sdg_reference, get_hybrid_engine


@st.cache_resource
def get_cached_sdg_ref():
    """Get cached SDG reference instance."""
    return get_sdg_reference()


@st.cache_resource
def get_cached_engine(
    model_name=None,
    similarity_threshold: float = 0.3,
    bias_corrections: dict = None,
    use_custom_thresholds: bool = False,
    custom_sdg_thresholds: dict = None,
):
    """Get cached ST-only alignment engine (legacy fallback)."""
    from src.alignment_engine import AlignmentEngine

    bias = bias_corrections or {}
    engine = AlignmentEngine(
        model_name=model_name,
        enable_sdg17_correction=bias.get(17, True),
        enable_sdg11_correction=bias.get(11, True),
        use_custom_thresholds=use_custom_thresholds,
        custom_sdg_thresholds=custom_sdg_thresholds,
    )
    engine.similarity_threshold = similarity_threshold
    return engine


@st.cache_resource
def get_cached_hybrid_engine(
    model_name: str,
    similarity_threshold: float,
    ensemble_mode: str,
    bias_corrections: dict = None,
    use_custom_thresholds: bool = False,
    custom_sdg_thresholds: dict = None,
):
    """Get cached hybrid alignment engine with sdgBERT support (V2 primary)."""
    return get_hybrid_engine(
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        ensemble_mode=ensemble_mode,
        bias_corrections=bias_corrections,
        use_custom_thresholds=use_custom_thresholds,
        custom_sdg_thresholds=custom_sdg_thresholds,
    )
