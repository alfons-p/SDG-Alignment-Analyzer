"""Results router — compare, list all results."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, get_current_user
from backend.app.models import Analysis, User
from backend.app.schemas.analysis import CompareRequest
from backend.app.services.aggregation import compute_multi_report_comparison

router = APIRouter(prefix="/api/results", tags=["results"])


@router.post("/compare")
def compare_results(body: CompareRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if len(body.analysis_ids) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least 2 analysis IDs required")

    # A user can compare their own analyses and any published one. With a single
    # admin uploading everything, a user-scoped filter would return nothing for
    # other viewers (data-contract C#4).
    analyses = (
        db.query(Analysis)
        .filter(
            Analysis.id.in_(body.analysis_ids),
            Analysis.status == "completed",
            or_(Analysis.user_id == user.id, Analysis.published.is_(True)),
        )
        .all()
    )

    found_ids = {a.id for a in analyses}
    missing = set(body.analysis_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analyses not found or not completed: {', '.join(missing)}",
        )

    results = [a.result for a in analyses if a.result]
    comparison = compute_multi_report_comparison(results)

    return {"comparison": comparison, "sources": [a.original_filename for a in analyses]}
