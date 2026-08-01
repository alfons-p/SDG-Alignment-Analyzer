"""Analysis service — thin wrapper around the existing src/ pipeline.

No Streamlit dependencies. Pure file-based processing with DB-backed progress.
"""

import os
import gc
import shutil
import tempfile
import threading
import traceback
import logging
import multiprocessing as _mp
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.analysis import Analysis

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "backend/uploads"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _rss_mb() -> float:
    """Resident set size of this process in MB (-1 if unavailable)."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1048576
    except Exception:
        return -1.0


def _mps_mb() -> float:
    """Current MPS (Apple GPU) allocated memory in MB (-1 if unavailable). A
    steady climb across PDFs points to a GPU memory leak in the per-file
    model loading."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return torch.mps.current_allocated_memory() / 1048576
    except Exception:
        pass
    return -1.0


def _mem() -> str:
    return f"rss={_rss_mb():.0f}MB mps={_mps_mb():.0f}MB"


# ── Model caching ──────────────────────────────────────────────────────────
# The heavy objects (ActivityExtractor = BERT + spaCy; alignment engine =
# sentence-transformer + sdgBERT) were rebuilt for EVERY PDF, which leaked
# memory (RSS climbed ~35MB/file to 8GB over a batch, then the box swapped and
# stalled). Cache them keyed by their construction params — a batch reuses one
# instance — and serialize processing so only one PDF uses the models at a time.
_extractor_cache: dict = {}
_engine_cache: dict = {}
_PIPELINE_LOCK = threading.Lock()


def _get_extractor(min_words, max_words, use_bert_classifier, min_confidence, spacy_model, nofinancial, require_action_verb):
    key = (min_words, max_words, use_bert_classifier, round(min_confidence, 4), spacy_model, nofinancial, require_action_verb)
    ex = _extractor_cache.get(key)
    if ex is None:
        from src.activity_extractor import ActivityExtractor
        ex = ActivityExtractor(
            min_activity_length=min_words,
            max_activity_length=max_words,
            use_bert_classifier=use_bert_classifier,
            min_confidence=min_confidence,
            spacy_model=spacy_model,
            nofinancial=nofinancial,
            require_action_verb=require_action_verb,
        )
        _extractor_cache[key] = ex
        logger.info(f"[cache] built ActivityExtractor {key} {_mem()}")
    return ex


def _get_engine(use_hybrid, model_name, similarity_threshold, ensemble_mode, bias, use_custom_thresholds, sdg_thresholds):
    key = (
        use_hybrid, model_name, round(similarity_threshold, 4), ensemble_mode,
        tuple(sorted((bias or {}).items())), use_custom_thresholds,
        tuple(sorted((sdg_thresholds or {}).items())),
    )
    eng = _engine_cache.get(key)
    if eng is None:
        if use_hybrid:
            from src.hybrid_alignment_engine import HybridAlignmentEngine
            eng = HybridAlignmentEngine(
                model_name=model_name,
                similarity_threshold=similarity_threshold,
                use_sdg_bert=True,
                ensemble_mode=ensemble_mode,
                enable_sdg17_correction=(bias or {}).get(17, True),
                enable_sdg11_correction=(bias or {}).get(11, True),
                enable_sdg14_correction=(bias or {}).get(14, True),
                enable_sdg4_correction=(bias or {}).get(4, True),
                enable_sdg6_correction=(bias or {}).get(6, True),
                enable_sdg8_correction=(bias or {}).get(8, True),
                enable_sdg10_correction=(bias or {}).get(10, True),
                enable_sdg12_correction=(bias or {}).get(12, True),
                enable_sdg16_correction=(bias or {}).get(16, True),
                use_custom_thresholds=use_custom_thresholds,
                custom_sdg_thresholds=sdg_thresholds,
            )
        else:
            from src.alignment_engine import AlignmentEngine
            eng = AlignmentEngine(
                model_name=model_name,
                enable_sdg17_correction=(bias or {}).get(17, True),
                enable_sdg11_correction=(bias or {}).get(11, True),
                use_custom_thresholds=use_custom_thresholds,
                custom_sdg_thresholds=sdg_thresholds,
            )
            eng.similarity_threshold = similarity_threshold
        _engine_cache[key] = eng
        logger.info(f"[cache] built alignment engine (hybrid={use_hybrid}) {_mem()}")
    return eng


def _cleanup_after_file():
    """Free per-PDF intermediates (not the cached models) after each analysis."""
    gc.collect()
    try:
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# ── Worker-process recycling ────────────────────────────────────────────────
# Profiling proved the per-PDF memory growth (~150MB/file, RSS 1GB→8GB over a
# batch, then the box swaps and stalls) is NATIVE allocator memory from repeated
# torch/numpy inference — not any Python object, so gc/empty_cache can't reclaim
# it in-process. The only reliable fix is to run the analysis in a child process
# and recycle it every N files: the OS reclaims everything when the child exits.
# The backend (parent) process therefore stays small; peak memory is bounded to
# ~one model set + N files' worth, then resets.
BATCH_WORKER_RECYCLE = int(os.getenv("BATCH_WORKER_RECYCLE", "20"))  # 0 = run inline (no subprocess)
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    if _pool is None:
        # A spawned child is a fresh interpreter that must be able to import the
        # `backend` / `src` packages — put the project root on PYTHONPATH so it
        # inherits it. (spawn, not fork: safe with torch/MPS already imported.)
        pp = os.environ.get("PYTHONPATH", "")
        if _PROJECT_ROOT not in pp.split(os.pathsep):
            os.environ["PYTHONPATH"] = _PROJECT_ROOT + (os.pathsep + pp if pp else "")
        ctx = _mp.get_context("spawn")
        _pool = ctx.Pool(processes=1, maxtasksperchild=BATCH_WORKER_RECYCLE)
        logger.info(f"[pool] spawned analysis worker, recycle every {BATCH_WORKER_RECYCLE} files")
    return _pool


def _run_in_worker(kwargs: dict) -> dict:
    """Entry point executed in the recycled child process. No DB, no progress
    callback (not picklable) — pure PDF→result computation. Returns the child's
    RSS under the reserved key `_worker_rss_mb` for leak monitoring."""
    result = _process_pdf_backend(**kwargs)
    try:
        result["_worker_rss_mb"] = round(_rss_mb())
    except Exception:
        pass
    return result


def _extract_activities_from_pdf(pdf_bytes: bytes, filename: str, min_words: int, max_words: int, top_activities: Optional[int], use_bert_classifier: bool = True, min_confidence: float = 0.7, spacy_model: str = "en_core_web_sm", nofinancial: bool = False, require_action_verb: bool = False, progress_callback: callable = None) -> dict:
    """Non-Streamlit version of activity extraction."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name

        metadata = _extract_metadata_from_filename(filename)
        extractor = _get_extractor(
            min_words, max_words, use_bert_classifier, min_confidence,
            spacy_model, nofinancial, require_action_verb,
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

    bias = bias_corrections or {}
    cb = progress_callback or (lambda p, s: None)

    # Serialize the model-heavy work: only one PDF uses the cached models at a
    # time. Bounds memory and prevents concurrent model use across overlapping
    # background tasks.
    with _PIPELINE_LOCK:
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

        # Step 3: Load alignment model (cached across PDFs)
        num_activities = activities_data.get("total_activities", 0)
        cb(20.0, "Loading SDG alignment model...")

        start_time = time.time()

        cb(30.0, f"Aligning {num_activities} activities with SDGs...")

        engine = _get_engine(
            use_hybrid, model_name, similarity_threshold, ensemble_mode,
            bias, use_custom_thresholds, sdg_thresholds,
        )

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

        import time as _time
        _t0 = _time.monotonic()
        logger.info(f"[PROC start] {analysis.original_filename} id={analysis_id[:8]} {_mem()}")

        proc_kwargs = dict(
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
        )

        if BATCH_WORKER_RECYCLE > 0:
            # Run in the recycled child process — bounds native memory. Progress
            # callbacks don't cross the process boundary, so the bar jumps
            # 0→100 per file; the job status transitions still work.
            with _pool_lock:
                pool = _get_pool()
            result = pool.apply(_run_in_worker, (proc_kwargs,))
            worker_rss = result.pop("_worker_rss_mb", None) if isinstance(result, dict) else None
            if worker_rss is not None:
                logger.info(f"[PROC worker] id={analysis_id[:8]} child_rss={worker_rss}MB")
        else:
            result = _process_pdf_backend(progress_callback=progress_callback, **proc_kwargs)

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
        logger.info(
            f"[PROC done] {analysis.original_filename} id={analysis_id[:8]} "
            f"status={analysis.status} elapsed={_time.monotonic() - _t0:.1f}s {_mem()}"
        )

    except Exception as e:
        logger.error(f"[PROC crash] id={analysis_id[:8]} {type(e).__name__}: {e} {_mem()}")
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = f"{e}\n\n{traceback.format_exc()}"
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        _cleanup_after_file()
        db.close()
