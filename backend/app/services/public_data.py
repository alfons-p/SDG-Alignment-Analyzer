"""Aggregate published analyses into the public coverage payload the landing
page renders (data-contract Part B). No authentication; reads only rows flagged
`published`. Shape mirrors data/coverage.json in the design handoff."""

from datetime import datetime, timezone
from statistics import median
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models import Analysis


def _report_alignment(a: Analysis) -> dict:
    return (a.result or {}).get("report_alignment", {}) or {}


def _coverage(a: Analysis) -> dict[int, float]:
    cov = _report_alignment(a).get("coverage", {}) or {}
    return {int(k): float(v) for k, v in cov.items()}


def _goals_evidenced(cov: dict[int, float]) -> int:
    return sum(1 for n in range(1, 18) if cov.get(n, 0) > 0)


def _extraction_grade(total: int, page_count: int | None) -> str:
    if not page_count:
        return "unknown"
    per100 = total / page_count * 100
    if per100 >= 40:
        return "rich"
    if per100 >= 15:
        return "moderate"
    return "thin"


def _council_key(a: Analysis) -> str:
    return a.lga_code or f"{(a.council_name or '').lower()}|{(a.state or '').lower()}"


def build_public_coverage(db: Session) -> dict[str, Any]:
    analyses = (
        db.query(Analysis)
        .filter(Analysis.published.is_(True), Analysis.status == "completed")
        .all()
    )

    # Group reports by council; keep one entry per year (latest upload wins).
    councils: dict[str, dict[str, Any]] = {}
    years: set[int] = set()
    sum_aligned: dict[int, float] = {n: 0.0 for n in range(1, 18)}
    sum_total = 0

    for a in analyses:
        ra = _report_alignment(a)
        total = int(ra.get("total_activities", 0))
        cov = _coverage(a)
        page_count = (a.result or {}).get("metadata", {}).get("page_count")
        for n in range(1, 18):
            sum_aligned[n] += cov.get(n, 0) * total
        sum_total += total
        if a.year:
            years.add(a.year)

        key = _council_key(a)
        c = councils.setdefault(
            key,
            {
                "lga_code": a.lga_code,
                "name": a.council_name or a.original_filename,
                "state": a.state,
                "by_year": {},
            },
        )
        year_key = str(a.year) if a.year else "unknown"
        c["by_year"][year_key] = {
            "goals_evidenced": _goals_evidenced(cov),
            "activities": total,
            "extraction": _extraction_grade(total, page_count),
        }

    council_list = []
    for c in councils.values():
        by_year = c["by_year"]
        latest = max(by_year.keys()) if by_year else None
        council_list.append(
            {
                "lga_code": c["lga_code"],
                "name": c["name"],
                "state": c["state"],
                "goals_evidenced": by_year[latest]["goals_evidenced"] if latest else None,
                "years_available": len(by_year),
                "by_year": by_year,
            }
        )

    national = _national(council_list, sum_aligned, sum_total)

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "years": sorted(years),
        "national": national,
        "councils": council_list,
    }


def _national(council_list: list[dict], sum_aligned: dict[int, float], sum_total: int) -> dict[str, Any]:
    evidenced = [c["goals_evidenced"] for c in council_list if c["goals_evidenced"] is not None]
    goal_shares = {
        str(n): round(sum_aligned[n] / sum_total, 4) if sum_total else 0.0 for n in range(1, 18)
    }
    return {
        "councils": len(council_list),
        "reports": sum(c["years_available"] for c in council_list),
        "activities": sum_total,
        "median_goals_evidenced": round(median(evidenced), 1) if evidenced else 0,
        "goal_shares": goal_shares,
    }
