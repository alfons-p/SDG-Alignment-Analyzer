"""SDG alignment processing for the dashboard."""

import time
import traceback
from typing import Dict, Any, Optional

from legacy.streamlit.dashboard.caching import get_cached_engine, get_cached_hybrid_engine
from legacy.streamlit.dashboard.processing.extraction import extract_activities_from_pdf_cached
from src.exceptions import SDGAnalyzerError


def align_activities_with_sdgs(
    activities_data: Dict[str, Any],
    model_name: str,
    similarity_threshold: float,
    use_hybrid: bool,
    ensemble_mode: str,
    bias_corrections: dict = None,
    use_custom_thresholds: bool = False,
    sdg_thresholds: dict = None,
    progress_bar=None,
) -> Dict[str, Any]:
    """Align extracted activities with SDGs.

    Args:
        bias_corrections: Dict of SDG number -> bool for per-SDG bias corrections.
    """
    start_time = time.time()

    if activities_data["total_activities"] == 0:
        return {"error": "No activities found in document"}

    try:
        if progress_bar:
            mode_label = "Hybrid" if use_hybrid else "Standard"
            progress_bar.progress(30, f"Loading AI models ({mode_label})...")

        if use_hybrid:
            engine = get_cached_hybrid_engine(
                model_name=model_name,
                similarity_threshold=similarity_threshold,
                ensemble_mode=ensemble_mode,
                bias_corrections=bias_corrections,
                use_custom_thresholds=use_custom_thresholds,
                custom_sdg_thresholds=sdg_thresholds,
            )
        else:
            engine = get_cached_engine(
                model_name,
                similarity_threshold,
                bias_corrections=bias_corrections,
                use_custom_thresholds=use_custom_thresholds,
                custom_sdg_thresholds=sdg_thresholds,
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
    model_name=None,
    similarity_threshold: float = 0.5,
    use_hybrid: bool = True,
    ensemble_mode: str = "weighted",
    min_words: int = 20,
    max_words: int = 500,
    top_activities: Optional[int] = None,
    bias_corrections: dict = None,
    use_custom_thresholds: bool = False,
    sdg_thresholds: dict = None,
    progress_bar=None,
) -> Dict[str, Any]:
    """Process uploaded PDF and return SDG alignment results (V2).

    Hybrid ensemble is the default. ST-only available as fallback.
    Per-SDG ensemble weights loaded automatically from SDG_ENSEMBLE_WEIGHTS.
    """
    # Step 1: Extract activities (cached)
    if progress_bar:
        progress_bar.progress(10, "Extracting activities from PDF (cached)...")

    activities_data = extract_activities_from_pdf_cached(
        uploaded_file.getvalue(),
        uploaded_file.name,
        min_words,
        max_words,
        top_activities,
    )

    if "error" in activities_data:
        return activities_data

    # Step 2: Align with SDGs
    return align_activities_with_sdgs(
        activities_data,
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        use_hybrid=use_hybrid,
        ensemble_mode=ensemble_mode,
        bias_corrections=bias_corrections,
        use_custom_thresholds=use_custom_thresholds,
        sdg_thresholds=sdg_thresholds,
        progress_bar=progress_bar,
    )
