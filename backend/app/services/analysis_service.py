"""Analysis service — thin wrapper around the existing src/ pipeline.

No Streamlit dependencies. Pure file-based processing with DB-backed progress.
"""

import os
import shutil
import tempfile
import traceback
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.analysis import Analysis

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "backend/uploads"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _extract_activities_from_pdf(pdf_bytes: bytes, filename: str, min_words: int, max_words: int, top_activities: Optional[int], use_bert_classifier: bool = True, min_confidence: float = 0.7, spacy_model: str = "en_core_web_sm", nofinancial: bool = False, require_action_verb: bool = False, progress_callback: callable = None) -> dict:
    """Non-Streamlit version of activity extraction."""
    from src.activity_extractor import ActivityExtractor

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name

        metadata = _extract_metadata_from_filename(filename)
        extractor = ActivityExtractor(
            min_activity_length=min_words,
            max_activity_length=max_words,
            use_bert_classifier=use_bert_classifier,
            min_confidence=min_confidence,
            spacy_model=spacy_model,
            nofinancial=nofinancial,
            require_action_verb=require_action_verb,
        )
        activities_data = extractor.extract_from_pdf(tmp_path, progress_callback=progress_callback)
        activities_data["source"] = filename
        activities_data["metadata"]["year"] = metadata["year"]
        activities_data["metadata"]["state"] = metadata["state"]
        activities_data["metadata"]["urban_rural"] = metadata["urban_rural"]
        activities_data["metadata"]["source"] = filename

        if top_activities and top_activities > 0:
            activities_data["activities"] = activities_data["activities"][:top_activities]

        return activities_data
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


def _extract_metadata_from_filename(filename: str) -> dict[str, str]:
    """Extract year, state, council, and urban/rural classification from filename."""
    import re

    metadata = {"year": "", "state": "", "council_name": "", "urban_rural": "", "source": filename}

    year_match = re.search(r"20\d{2}", filename)
    if year_match:
        metadata["year"] = year_match.group(0)

    state_patterns = ["VIC", "NSW", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
    for state in state_patterns:
        if state in filename.upper():
            metadata["state"] = state
            break

    filename_lower = filename.lower()
    if "urban" in filename_lower:
        metadata["urban_rural"] = "Urban"
    elif "rural" in filename_lower:
        metadata["urban_rural"] = "Rural"

    standardized_match = re.match(
        r"([A-Z]{2,3})_([^_]+)_(Urban|Rural|nan)_([0-9]{4})",
        filename,
        re.IGNORECASE,
    )
    if standardized_match:
        metadata["state"] = standardized_match.group(1).upper()
        metadata["council_name"] = standardized_match.group(2).replace("_", " ")
        metadata["urban_rural"] = standardized_match.group(3)
        metadata["year"] = standardized_match.group(4)

    return metadata


def _process_pdf_backend(
    pdf_bytes: bytes,
    filename: str,
    model_name: str = "voyager205/sdg-variant-finetuned",
    similarity_threshold: float = 0.5,
    use_hybrid: bool = True,
    ensemble_mode: str = "weighted",
    min_words: int = 20,
    max_words: int = 500,
    top_activities: Optional[int] = None,
    bias_corrections: dict = None,
    use_custom_thresholds: bool = False,
    sdg_thresholds: dict = None,
    use_bert_classifier: bool = True,
    min_confidence: float = 0.7,
    spacy_model: str = "en_core_web_sm",
    nofinancial: bool = False,
    require_action_verb: bool = False,
    progress_callback: callable = None,
) -> dict:
    """Process a PDF through the full pipeline — no Streamlit/DB. Returns result dict."""
    import time

    from src.hybrid_alignment_engine import HybridAlignmentEngine

    bias = bias_corrections or {}
    cb = progress_callback or (lambda p, s: None)

    # Step 1-2: Extract text from PDF and split into activities
    cb(5.0, "Starting activity extraction...")
    activities_data = _extract_activities_from_pdf(
        pdf_bytes=pdf_bytes,
        filename=filename,
        min_words=min_words,
        max_words=max_words,
        top_activities=top_activities,
        use_bert_classifier=use_bert_classifier,
        min_confidence=min_confidence,
        spacy_model=spacy_model,
        nofinancial=nofinancial,
        require_action_verb=require_action_verb,
        progress_callback=cb,
    )

    if "error" in activities_data:
        return activities_data

    if activities_data.get("total_activities", 0) == 0:
        return {"error": "No activities found in document"}

    # Step 3: Load alignment model
    num_activities = activities_data.get("total_activities", 0)
    cb(20.0, f"Loading SDG alignment model...")

    start_time = time.time()

    cb(30.0, f"Aligning {num_activities} activities with SDGs...")

    if use_hybrid:
        engine = HybridAlignmentEngine(
            model_name=model_name,
            similarity_threshold=similarity_threshold,
            use_sdg_bert=True,
            ensemble_mode=ensemble_mode,
            enable_sdg17_correction=bias.get(17, True),
            enable_sdg11_correction=bias.get(11, True),
            enable_sdg14_correction=bias.get(14, True),
            enable_sdg4_correction=bias.get(4, True),
            enable_sdg6_correction=bias.get(6, True),
            enable_sdg8_correction=bias.get(8, True),
            enable_sdg10_correction=bias.get(10, True),
            enable_sdg12_correction=bias.get(12, True),
            enable_sdg16_correction=bias.get(16, True),
            use_custom_thresholds=use_custom_thresholds,
            custom_sdg_thresholds=sdg_thresholds,
        )
    else:
        from src.alignment_engine import AlignmentEngine
        engine = AlignmentEngine(
            model_name=model_name,
            enable_sdg17_correction=bias.get(17, True),
            enable_sdg11_correction=bias.get(11, True),
            use_custom_thresholds=use_custom_thresholds,
            custom_sdg_thresholds=sdg_thresholds,
        )
        engine.similarity_threshold = similarity_threshold

    cb(50.0, f"Computing SDG scores for {num_activities} activities...")
    results = engine.align_report(activities_data, show_progress=False, use_cache=True)

    cb(95.0, "Generating summary and statistics...")
    elapsed = time.time() - start_time
    logger.info(f"Processed {filename}: {len(results.get('activities', []))} activities in {elapsed:.1f}s")

    return results


def update_job_progress(analysis_id: str, db: Session, progress: float, step: str):
    """Update progress on an Analysis row. Called from background thread."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis:
        analysis.progress = progress
        analysis.current_step = step
        db.commit()


def run_analysis_sync(analysis_id: str, db_session_factory):
    """Run analysis synchronously in a background thread. Updates DB directly."""
    db = db_session_factory()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return

        analysis.status = "processing"
        analysis.progress = 0.0
        db.commit()

        if not analysis.file_path or not os.path.exists(analysis.file_path):
            analysis.status = "failed"
            analysis.error_message = "Uploaded file no longer exists — it may have been deleted"
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        with open(analysis.file_path, "rb") as f:
            pdf_bytes = f.read()

        settings = analysis.settings or {}

        def progress_callback(progress: float, step: str):
            update_job_progress(analysis_id, db, progress, step)

        def is_cancelled():
            db.refresh(analysis)
            return analysis.status not in ("queued", "processing")

        result = _process_pdf_backend(
            pdf_bytes=pdf_bytes,
            filename=analysis.original_filename,
            model_name=settings.get("model_name", "voyager205/sdg-variant-finetuned"),
            similarity_threshold=settings.get("similarity_threshold", 0.5),
            use_hybrid=settings.get("use_hybrid", True),
            ensemble_mode=settings.get("ensemble_mode", "weighted"),
            min_words=settings.get("min_words", 20),
            max_words=settings.get("max_words", 500),
            top_activities=settings.get("top_activities") if settings.get("top_activities", 0) > 0 else None,
            bias_corrections=settings.get("bias_corrections", {}),
            use_custom_thresholds=settings.get("use_custom_thresholds", False),
            sdg_thresholds=settings.get("sdg_thresholds", {}),
            use_bert_classifier=settings.get("use_bert_classifier", True),
            min_confidence=settings.get("min_confidence", 0.7),
            spacy_model=settings.get("spacy_model", "en_core_web_sm"),
            nofinancial=settings.get("nofinancial", False),
            require_action_verb=settings.get("require_action_verb", False),
            progress_callback=progress_callback,
        )

        if is_cancelled():
            return  # status already set by cancel endpoint

        if "error" in result:
            analysis.status = "failed"
            analysis.error_message = str(result["error"])
            if "traceback" in result:
                analysis.error_message = f"{result['error']}\n\n{result['traceback']}"
        else:
            analysis.status = "completed"
            analysis.result = result
            analysis.progress = 100.0
            analysis.current_step = "Complete"

        analysis.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = f"{e}\n\n{traceback.format_exc()}"
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
