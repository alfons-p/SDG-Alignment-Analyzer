"""Analysis router — upload, jobs, results, export."""

import hashlib
import os
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger("sdg.client")

from backend.app.dependencies import get_db, get_current_user, get_current_admin, SessionLocal
from backend.app.models import Analysis, User
from backend.app.services.identity import parse_report_identity
from backend.app.schemas.analysis import (
    ProcessingSettingsSchema,
    AnalysisJobResponse,
    AnalysisResultResponse,
    AnalysisSummary,
    ActivityPageResponse,
    AnalysisListItem,
    CompareRequest,
)
from backend.app.services.analysis_service import run_analysis_sync, UPLOADS_DIR
from backend.app.services.export_service import generate_csv_bytes, generate_json_bytes
from backend.app.services.pdf_service import generate_ledger_pdf, generate_statement_pdf

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "0"))  # 0 = no limit (Cloudflare still caps ~100MB)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _validate_settings(**kwargs) -> dict:
    """Validate and sanitize processing settings via Pydantic."""
    import json

    # Parse sdg_thresholds JSON if provided
    sdg_thresholds_json = kwargs.pop("sdg_thresholds_json", "{}")
    sdg_thresholds = kwargs.pop("sdg_thresholds", None)
    if sdg_thresholds is None:
        try:
            raw = json.loads(sdg_thresholds_json) if sdg_thresholds_json else {}
            sdg_thresholds = {int(k): v for k, v in raw.items()} if raw else {}
        except (json.JSONDecodeError, ValueError, TypeError):
            sdg_thresholds = {}

    # Wire enable_bias_corrections into bias_corrections dict
    enable_bias = kwargs.pop("enable_bias_corrections", True)
    bias_corrections = kwargs.pop("bias_corrections", None) or {}
    if not bias_corrections:
        bias_default = True if enable_bias else False
        bias_corrections = {n: bias_default for n in [17, 11, 14, 4, 6, 8, 10, 12, 16]}

    # Extract non-schema pipeline args (stored alongside schema fields)
    use_bert_classifier = kwargs.pop("use_bert_classifier", True)
    min_confidence = kwargs.pop("min_confidence", 0.7)
    spacy_model = kwargs.pop("spacy_model", "en_core_web_sm")
    nofinancial = kwargs.pop("nofinancial", False)
    require_action_verb = kwargs.pop("require_action_verb", False)

    validated = ProcessingSettingsSchema(
        **kwargs,
        bias_corrections=bias_corrections,
        sdg_thresholds=sdg_thresholds,
    )
    result = validated.model_dump()
    result["use_bert_classifier"] = use_bert_classifier
    result["min_confidence"] = min_confidence
    result["spacy_model"] = spacy_model
    result["nofinancial"] = nofinancial
    result["require_action_verb"] = require_action_verb
    return result


@router.post("/upload", response_model=AnalysisJobResponse, status_code=202)
def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_name: str = Query("voyager205/sdg-variant-finetuned"),
    similarity_threshold: float = Query(0.5),
    use_hybrid: bool = Query(True),
    ensemble_mode: str = Query("weighted"),
    min_words: int = Query(20),
    max_words: int = Query(500),
    top_activities: int = Query(0),
    enable_bias_corrections: bool = Query(True),
    use_bert_classifier: bool = Query(True),
    min_confidence: float = Query(0.7),
    use_custom_thresholds: bool = Query(False),
    sdg_thresholds_json: str = Query("{}"),
    spacy_model: str = Query("en_core_web_sm"),
    nofinancial: bool = Query(False),
    require_action_verb: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported")

    content = file.file.read()
    file_size = len(content)

    if MAX_UPLOAD_BYTES and file_size > MAX_UPLOAD_BYTES:
        max_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_mb:.0f}MB",
        )

    # Skip-if-exists: if this user already has a COMPLETED analysis for the same
    # council-year (parsed from the filename), don't create a duplicate. Only
    # dedup when identity is strong enough (year + council). Failed/queued runs
    # are not a match, so a re-drop retries them. Checked before writing the file
    # so skipped uploads leave nothing on disk.
    ident = parse_report_identity(file.filename)
    if ident["year"] and ident["council_name"]:
        dup_q = db.query(Analysis).filter(
            Analysis.user_id == user.id,
            Analysis.status == "completed",
            Analysis.council_name == ident["council_name"],
            Analysis.year == ident["year"],
        )
        dup_q = (
            dup_q.filter(Analysis.state == ident["state"])
            if ident["state"]
            else dup_q.filter(Analysis.state.is_(None))
        )
        existing = dup_q.first()
        if existing:
            existing.skipped = True
            existing.existing_id = existing.id
            return existing

    # Use cryptographic hash for stable dedup across processes
    file_hash = hashlib.sha256(content).hexdigest()[:12]
    file_path = UPLOADS_DIR / f"{Path(file.filename).stem}_{file_hash}.pdf"
    file_path.write_bytes(content)

    settings = _validate_settings(
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        use_hybrid=use_hybrid,
        ensemble_mode=ensemble_mode,
        min_words=min_words,
        max_words=max_words,
        top_activities=top_activities,
        enable_bias_corrections=enable_bias_corrections,
        use_bert_classifier=use_bert_classifier,
        min_confidence=min_confidence,
        use_custom_thresholds=use_custom_thresholds,
        sdg_thresholds_json=sdg_thresholds_json,
        spacy_model=spacy_model,
        nofinancial=nofinancial,
    )

    analysis = Analysis(
        user_id=user.id,
        status="queued",
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        settings=settings,
        council_name=ident["council_name"],
        state=ident["state"],
        year=ident["year"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    background_tasks.add_task(run_analysis_sync, analysis.id, SessionLocal)

    return analysis


class ClientLog(BaseModel):
    message: str
    level: str = "info"


@router.post("/client-log")
def client_log(body: ClientLog, user: User = Depends(get_current_user)):
    """Record a client-side event (e.g. batch-upload start/summary) in the
    server log, so a batch's shape survives even if the browser tab dies. Also
    means the backend log holds the file count the client never otherwise sends.
    Each line is stamped with the server's UTC time since the default log format
    carries no timestamp."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    msg = f"[client:{user.email} {ts}] {body.message[:500]}"
    (logger.warning if body.level == "warning" else logger.info)(msg)
    return {"ok": True}


@router.get("/jobs/{analysis_id}", response_model=AnalysisJobResponse)
def get_job_status(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    return analysis


@router.get("/results/{analysis_id}", response_model=AnalysisResultResponse)
def get_results(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status == "queued":
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Analysis not started yet")
    if analysis.status == "processing":
        return AnalysisResultResponse(
            id=analysis.id,
            original_filename=analysis.original_filename,
            status=analysis.status,
            settings=analysis.settings,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
        )
    if analysis.status == "failed":
        return AnalysisResultResponse(
            id=analysis.id,
            original_filename=analysis.original_filename,
            status="failed",
            error_message=analysis.error_message,
            settings=analysis.settings,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
        )

    result = analysis.result or {}
    summary = result.get("report_alignment")
    if summary:
        summary = _normalize_summary_keys(summary, result.get("source", ""), result)
    return AnalysisResultResponse(
        id=analysis.id,
        original_filename=analysis.original_filename,
        status="completed",
        summary=AnalysisSummary(**summary) if summary else None,
        activities=result.get("activities"),
        settings=analysis.settings,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )


@router.get("/results/{analysis_id}/summary", response_model=AnalysisSummary)
def get_result_summary(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status == "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Analysis failed: {analysis.error_message}")
    if analysis.status != "completed" or not analysis.result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Results not available — status: {analysis.status}")
    summary = analysis.result.get("report_alignment", {})
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No summary data")
    return AnalysisSummary(
        **_normalize_summary_keys(summary, analysis.result.get("source", ""), analysis.result)
    )


@router.get("/results/{analysis_id}/activities", response_model=ActivityPageResponse)
def get_result_activities(
    analysis_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sdg: Optional[int] = Query(None, ge=1, le=17),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status == "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Analysis failed: {analysis.error_message}")
    if analysis.status != "completed" or not analysis.result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Results not available — status: {analysis.status}")

    activities = analysis.result.get("activities", [])

    if sdg is not None:
        sdg_str = str(sdg)
        activities = [
            a for a in activities
            if (
                a.get("sdg_scores", {}).get(sdg) or a.get("sdg_scores", {}).get(sdg_str) or {}
            ).get("is_aligned", False)
        ]

    total = len(activities)
    start = (page - 1) * page_size
    paged = activities[start : start + page_size]

    return ActivityPageResponse(
        activities=paged, page=page, page_size=page_size, total=total, sdg_filter=sdg
    )


@router.get("/results/{analysis_id}/export/csv")
def export_results_csv(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status != "completed" or not analysis.result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Results not available — status: {analysis.status}")
    buf = generate_csv_bytes(analysis.result)
    filename = Path(analysis.original_filename).stem + "_alignment.csv"
    return StreamingResponse(buf, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/results/{analysis_id}/export/json")
def export_results_json(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status != "completed" or not analysis.result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Results not available — status: {analysis.status}")
    buf = generate_json_bytes(analysis.result)
    filename = Path(analysis.original_filename).stem + "_alignment.json"
    return StreamingResponse(buf, media_type="application/json", headers={"Content-Disposition": f"attachment; filename={filename}"})


def _pdf_response(analysis: Analysis, buf, suffix: str) -> StreamingResponse:
    filename = Path(analysis.original_filename).stem + f"_{suffix}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/results/{analysis_id}/export/pdf/statement")
def export_results_pdf_statement(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status != "completed" or not analysis.result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Results not available — status: {analysis.status}")
    buf = generate_statement_pdf(analysis.result, analysis.council_name, analysis.state, analysis.year, analysis.original_filename)
    return _pdf_response(analysis, buf, "statement")


@router.get("/results/{analysis_id}/export/pdf/ledger")
def export_results_pdf_ledger(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status != "completed" or not analysis.result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Results not available — status: {analysis.status}")
    buf = generate_ledger_pdf(analysis.result, analysis.council_name, analysis.state, analysis.year, analysis.original_filename)
    return _pdf_response(analysis, buf, "ledger")


@router.get("", response_model=list[AnalysisListItem])
def list_analyses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .limit(50)
        .all()
    )
    return analyses


@router.get("/admin/runs")
def admin_runs(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Every analysis with its publish state and headline metrics, for the admin
    runs table. Admin only (data-contract C#0)."""
    from backend.app.services.public_data import (
        _report_alignment,
        _coverage,
        _goals_evidenced,
        _extraction_grade,
    )

    analyses = db.query(Analysis).order_by(Analysis.created_at.desc()).limit(200).all()
    runs = []
    for a in analyses:
        ra = _report_alignment(a)
        cov = _coverage(a)
        total = int(ra.get("total_activities", 0))
        page_count = (a.result or {}).get("metadata", {}).get("page_count") if a.result else None
        runs.append(
            {
                "id": a.id,
                "council_name": a.council_name,
                "state": a.state,
                "year": a.year,
                "status": a.status,
                "published": a.published,
                "total_activities": total,
                "goals_evidenced": _goals_evidenced(cov) if cov else None,
                "extraction": _extraction_grade(total, page_count) if a.status == "completed" else None,
                "created_at": a.created_at,
            }
        )
    return runs


@router.post("/{analysis_id}/cancel")
def cancel_analysis(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cancel a running analysis."""
    from datetime import datetime, timezone
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.status not in ("queued", "processing"):
        raise HTTPException(409, detail="Analysis is not running")
    analysis.status = "failed"
    analysis.error_message = "Cancelled by user"
    analysis.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "cancelled"}


@router.post("/{analysis_id}/publish")
def publish_analysis(analysis_id: str, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Make a completed analysis publicly readable. Admin only (data-contract C#0)."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only completed analyses can be published")
    analysis.published = True
    db.commit()
    return {"id": analysis.id, "published": True}


@router.post("/admin/publish-all")
def publish_all(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Publish every completed, not-yet-published analysis in one call. Single
    bulk UPDATE so it scales to large batches. Admin only."""
    count = (
        db.query(Analysis)
        .filter(Analysis.status == "completed", Analysis.published.is_(False))
        .update({Analysis.published: True}, synchronize_session=False)
    )
    db.commit()
    return {"published": count}


@router.post("/{analysis_id}/unpublish")
def unpublish_analysis(analysis_id: str, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    analysis.published = False
    db.commit()
    return {"id": analysis.id, "published": False}


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _get_user_analysis(analysis_id, user, db)
    if analysis.file_path and os.path.exists(analysis.file_path):
        try:
            os.remove(analysis.file_path)
        except OSError:
            pass
    db.delete(analysis)
    db.commit()


def _get_user_analysis(analysis_id: str, user: User, db: Session) -> Analysis:
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


def _normalize_summary_keys(summary: dict, source: str = "", result: dict | None = None) -> dict:
    """Convert string SDG keys to int, recompute gaps as coverage==0 (ranked by
    mean, per data-contract C#3), and attach extraction-quality metrics (C#5).
    Injects source if missing."""
    if summary.get("mean_scores"):
        summary["mean_scores"] = {int(k): v for k, v in summary["mean_scores"].items()}
    if summary.get("coverage"):
        summary["coverage"] = {int(k): v for k, v in summary["coverage"].items()}
    if "source" not in summary:
        summary["source"] = source

    coverage = summary.get("coverage") or {}
    mean_scores = summary.get("mean_scores") or {}
    if coverage:
        from src.config.sdg_definitions import SDG_DEFINITIONS

        gaps = [
            {"sdg": n, "name": SDG_DEFINITIONS[n]["name"], "mean_score": mean_scores.get(n, 0.0), "coverage": 0.0}
            for n in range(1, 18)
            if coverage.get(n, 0) == 0
        ]
        summary["gaps"] = sorted(gaps, key=lambda g: g["mean_score"], reverse=True)

    if result is not None:
        activities = result.get("activities", []) or []
        page_count = (result.get("metadata") or {}).get("page_count")
        total = summary.get("total_activities", len(activities))
        summary["page_count"] = page_count
        summary["barren_activities"] = sum(1 for a in activities if a.get("num_aligned", 0) == 0)
        if page_count:
            summary["activities_per_100_pages"] = round(total / page_count * 100, 1)
    return summary
