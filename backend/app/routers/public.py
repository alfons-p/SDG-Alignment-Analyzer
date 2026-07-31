"""Public, unauthenticated read routes for published analyses (data-contract
Part B Option 2). Serves the landing page and per-council pages to anyone."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db
from backend.app.models import Analysis
from backend.app.services.public_data import build_public_coverage, _report_alignment, _coverage

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/coverage")
def public_coverage(db: Session = Depends(get_db)):
    """The full landing payload: national headline + every published council."""
    return build_public_coverage(db)


@router.get("/national")
def public_national(db: Session = Depends(get_db)):
    return build_public_coverage(db)["national"]


@router.get("/councils/{lga_code}")
def public_council(lga_code: str, db: Session = Depends(get_db)):
    """One council across all its published years, with each report's summary."""
    analyses = (
        db.query(Analysis)
        .filter(
            Analysis.lga_code == lga_code,
            Analysis.published.is_(True),
            Analysis.status == "completed",
        )
        .all()
    )
    if not analyses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No published analysis for this council")

    a0 = analyses[0]
    reports = []
    for a in sorted(analyses, key=lambda x: x.year or 0, reverse=True):
        ra = _report_alignment(a)
        cov = _coverage(a)
        reports.append(
            {
                "analysis_id": a.id,
                "year": a.year,
                "total_activities": ra.get("total_activities", 0),
                "coverage": cov,
                "goals_evidenced": sum(1 for n in range(1, 18) if cov.get(n, 0) > 0),
                "top_sdgs": ra.get("top_sdgs", [])[:5],
            }
        )

    return {
        "lga_code": a0.lga_code,
        "name": a0.council_name,
        "state": a0.state,
        "reports": reports,
    }
