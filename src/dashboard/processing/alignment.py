"""SDG alignment processing for the dashboard."""

import time
import traceback
from typing import Dict, Any, Optional

from src.dashboard.caching import get_cached_engine, get_cached_hybrid_engine
from src.dashboard.processing.extraction import extract_activities_from_pdf_cached
from src.exceptions import SDGAnalyzerError


def align_activities_with_sdgs(
    activities_data: Dict[str, Any],
    model_name: str,
    similarity_threshold: float,
    use_hybrid: bool,
    ensemble_mode: str,
    sdg_bert_weight: float,
    st_weight: float,
    enable_sdg17_correction: bool = True,
    enable_sdg11_correction: bool = True,
    use_custom_thresholds: bool = False,
    sdg_thresholds: dict = None,
    progress_bar=None
) -> Dict[str, Any]:
    """Align extracted activities with SDGs using the specified engine and threshold.

    This runs every time the threshold or model settings change.

    Args:
        activities_data: Dictionary with extracted activities
        model_name: Name of the sentence transformer model
        similarity_threshold: Minimum similarity threshold for alignment
        use_hybrid: Whether to use hybrid ensemble (sdgBERT + ST)
        ensemble_mode: How to combine models ('weighted', 'fallback', 'single')
        sdg_bert_weight: Weight for sdgBERT in ensemble
        st_weight: Weight for sentence transformer in ensemble
        enable_sdg17_correction: Enable SDG 17 bias correction
        enable_sdg11_correction: Enable SDG 11 bias correction
        use_custom_thresholds: Use custom SDG-specific thresholds
        sdg_thresholds: Dict of SDG -> threshold values
        progress_bar: Optional Streamlit progress bar

    Returns:
        Dictionary with alignment results or error information
    """
    start_time = time.time()

    if activities_data['total_activities'] == 0:
        return {"error": "No activities found in document"}

    try:
        if progress_bar:
            progress_bar.progress(30, f"Loading AI models ({'Hybrid' if use_hybrid else 'Standard'})...")

        # Align with SDGs using appropriate engine
        if use_hybrid:
            engine = get_cached_hybrid_engine(
                model_name=model_name,
                similarity_threshold=similarity_threshold,
                ensemble_mode=ensemble_mode,
                sdg_bert_weight=sdg_bert_weight,
                st_weight=st_weight,
                enable_sdg17_correction=enable_sdg17_correction,
                enable_sdg11_correction=enable_sdg11_correction,
                use_custom_thresholds=use_custom_thresholds,
                custom_sdg_thresholds=sdg_thresholds
            )
        else:
            engine = get_cached_engine(
                model_name,
                similarity_threshold,
                enable_sdg17_correction=enable_sdg17_correction,
                enable_sdg11_correction=enable_sdg11_correction,
                use_custom_thresholds=use_custom_thresholds,
                custom_sdg_thresholds=sdg_thresholds
            )

        if progress_bar:
            progress_bar.progress(60, "Computing SDG alignment scores...")

        results = engine.align_report(activities_data, show_progress=False)

        elapsed_time = time.time() - start_time
        if progress_bar:
            progress_bar.progress(100, f"Complete! ({elapsed_time:.1f}s)")

        return results

    except SDGAnalyzerError as e:
        return {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}
    except Exception as e:
        return {"error": str(e), "error_type": "UnexpectedError", "traceback": traceback.format_exc()}


def process_pdf(
    uploaded_file,
    model_name: str = "all-mpnet-base-v2",
    similarity_threshold: float = 0.3,
    use_hybrid: bool = False,
    ensemble_mode: str = "weighted",
    sdg_bert_weight: float = 0.55,
    st_weight: float = 0.45,
    min_words: int = 20,
    max_words: int = 500,
    top_activities: Optional[int] = None,
    enable_sdg17_correction: bool = True,
    enable_sdg11_correction: bool = True,
    use_custom_thresholds: bool = False,
    sdg_thresholds: dict = None,
    progress_bar=None
) -> Dict[str, Any]:
    """Process uploaded PDF and return results with metadata.

    This is the main entry point for PDF processing, combining extraction
    and alignment steps.

    Args:
        uploaded_file: Streamlit UploadedFile object
        model_name: Name of the sentence transformer model
        similarity_threshold: Minimum similarity threshold for alignment
        use_hybrid: Whether to use hybrid ensemble
        ensemble_mode: How to combine models
        sdg_bert_weight: Weight for sdgBERT in ensemble
        st_weight: Weight for sentence transformer in ensemble
        min_words: Minimum word count for activities
        max_words: Maximum word count for activities
        top_activities: Limit to top N activities (None for all)
        enable_sdg17_correction: Enable SDG 17 bias correction
        enable_sdg11_correction: Enable SDG 11 bias correction
        use_custom_thresholds: Use custom SDG-specific thresholds
        sdg_thresholds: Dict of SDG -> threshold values
        progress_bar: Optional Streamlit progress bar

    Returns:
        Dictionary with alignment results
    """
    # Step 1: Extract activities (cached - only runs if file or extraction params change)
    if progress_bar:
        progress_bar.progress(10, "Extracting activities from PDF (cached)...")

    activities_data = extract_activities_from_pdf_cached(
        uploaded_file.getvalue(),
        uploaded_file.name,
        min_words,
        max_words,
        top_activities
    )

    if "error" in activities_data:
        return activities_data

    # Step 2: Align with SDGs (runs every time threshold/model changes)
    return align_activities_with_sdgs(
        activities_data,
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        use_hybrid=use_hybrid,
        ensemble_mode=ensemble_mode,
        sdg_bert_weight=sdg_bert_weight,
        st_weight=st_weight,
        enable_sdg17_correction=enable_sdg17_correction,
        enable_sdg11_correction=enable_sdg11_correction,
        use_custom_thresholds=use_custom_thresholds,
        sdg_thresholds=sdg_thresholds,
        progress_bar=progress_bar
    )