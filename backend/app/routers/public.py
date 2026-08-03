"""Public, unauthenticated read routes for published analyses (data-contract
Part B Option 2). Serves the landing page and per-council pages to anyone."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db
from backend.app.services.public_data import build_public_coverage, build_council_detail

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/coverage")
def public_coverage(db: Session = Depends(get_db)):
    """The full landing payload: national headline + every published council."""
    return build_public_coverage(db)


@router.get("/national")
def public_national(db: Session = Depends(get_db)):
    return build_public_coverage(db)["national"]


@router.get("/councils/{code}")
def public_council(code: str, db: Session = Depends(get_db)):
    """One council across all its published years — per-Goal counts, mean scores
    and top evidence passages. `code` is the slug from the coverage payload."""
    detail = build_council_detail(db, code)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No published analysis for this council")
    return detail
