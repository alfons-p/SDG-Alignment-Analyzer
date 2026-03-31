"""Cached resource loaders for the SDG Alignment Analyzer dashboard.

This module provides Streamlit-cached versions of resource-heavy operations
like model loading and SDG reference initialization.
"""

import streamlit as st

from src.dashboard.utils import get_sdg_reference, get_hybrid_engine


@st.cache_resource
def get_cached_sdg_ref():
    """Get cached SDG reference instance."""
    return get_sdg_reference()


@st.cache_resource
def get_cached_engine(
    model_name: str = "all-mpnet-base-v2",
    similarity_threshold: float = 0.3,
    enable_sdg17_correction: bool = True,
    enable_sdg11_correction: bool = True,
    use_custom_thresholds: bool = False,
    custom_sdg_thresholds: dict = None
):
    """Get cached alignment engine instance.

    Args:
        model_name: Name of the sentence transformer model
        similarity_threshold: Minimum similarity threshold for alignment
        enable_sdg17_correction: Enable SDG 17 bias correction
        enable_sdg11_correction: Enable SDG 11 bias correction
        use_custom_thresholds: Use custom SDG-specific thresholds
        custom_sdg_thresholds: Dict of SDG -> threshold values

    Returns:
        Cached AlignmentEngine instance
    """
    from src.alignment_engine import AlignmentEngine
    engine = AlignmentEngine(
        model_name=model_name,
        enable_sdg17_correction=enable_sdg17_correction,
        enable_sdg11_correction=enable_sdg11_correction,
        use_custom_thresholds=use_custom_thresholds,
        custom_sdg_thresholds=custom_sdg_thresholds
    )
    engine.similarity_threshold = similarity_threshold
    return engine


@st.cache_resource
def get_cached_hybrid_engine(
    model_name: str,
    similarity_threshold: float,
    ensemble_mode: str,
    sdg_bert_weight: float,
    st_weight: float,
    enable_sdg17_correction: bool = True,
    enable_sdg11_correction: bool = True,
    use_custom_thresholds: bool = False,
    custom_sdg_thresholds: dict = None
):
    """Get cached hybrid alignment engine with sdgBERT support.

    Args:
        model_name: Name of the sentence transformer model
        similarity_threshold: Minimum similarity threshold for alignment
        ensemble_mode: How to combine models ('weighted', 'fallback', 'single')
        sdg_bert_weight: Weight for sdgBERT in ensemble
        st_weight: Weight for sentence transformer in ensemble
        enable_sdg17_correction: Enable SDG 17 bias correction
        enable_sdg11_correction: Enable SDG 11 bias correction
        use_custom_thresholds: Use custom SDG-specific thresholds
        custom_sdg_thresholds: Dict of SDG -> threshold values

    Returns:
        Cached HybridAlignmentEngine instance
    """
    return get_hybrid_engine(
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        ensemble_mode=ensemble_mode,
        sdg_bert_weight=sdg_bert_weight,
        st_weight=st_weight,
        enable_sdg17_correction=enable_sdg17_correction,
        enable_sdg11_correction=enable_sdg11_correction,
        use_custom_thresholds=use_custom_thresholds,
        custom_sdg_thresholds=custom_sdg_thresholds
    )