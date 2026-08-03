"""Aggregate published analyses into the public coverage payload the landing
page renders (data-contract Part B). No authentication; reads only rows flagged
`published`. Shape mirrors data/coverage.json in the design handoff."""

import re
from datetime import datetime, timezone
from statistics import median
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.models import Analysis


def _report_alignment(a: Analysis) -> dict:
    return (a.result or {}).get("report_alignment", {}) or {}


def _class(a: Analysis) -> Optional[str]:
    """Peer-group setting for the Browse filter. Derived from the filename's
    Urban/Rural marker (the only peer dimension we carry)."""
    return ((a.result or {}).get("metadata", {}) or {}).get("urban_rural") or None


def council_slug(a: Analysis) -> str:
    """Stable URL id for a council. We have no ABS lga_code on most rows, so key
    on state + normalised name, e.g. 'nsw-bayside'."""
    if a.lga_code:
        return str(a.lga_code)
    name = re.sub(r"[^a-z0-9]+", "-", (a.council_name or "").lower()).strip("-")
    return f"{(a.state or 'xx').lower()}-{name}"


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
                "code": council_slug(a),
                "lga_code": a.lga_code,
                "name": a.council_name or a.original_filename,
                "state": a.state,
                "class": _class(a),
                "by_year": {},
            },
        )
        goals = [n for n in range(1, 18) if cov.get(n, 0) > 0]
        year_key = str(a.year) if a.year else "unknown"
        c["by_year"][year_key] = {
            "goals_evidenced": len(goals),
            "goals": goals,
            "activities": total,
            "extraction": _extraction_grade(total, page_count),
        }

    council_list = []
    for c in councils.values():
        by_year = c["by_year"]
        # newest numeric year for the top-level (map/list) mirror
        num_years = [y for y in by_year if y != "unknown"]
        latest = max(num_years) if num_years else (max(by_year) if by_year else None)
        top = by_year.get(latest, {}) if latest else {}
        council_list.append(
            {
                "code": c["code"],
                "lga_code": c["lga_code"],
                "name": c["name"],
                "state": c["state"],
                "class": c["class"],
                "goals_evidenced": top.get("goals_evidenced"),
                "goals": top.get("goals", []),
                "years_available": len(by_year),
                "latest_year": int(latest) if latest and latest != "unknown" else None,
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


def _year_detail(a: Analysis) -> dict[str, Any]:
    """Per-year council detail: counts + mean scores per Goal, and the top
    evidence passages per Goal (data-contract council payload)."""
    ra = _report_alignment(a)
    total = int(ra.get("total_activities", 0))
    means_raw = ra.get("mean_scores", {}) or {}
    acts = (a.result or {}).get("activities", []) or []

    counts = {n: 0 for n in range(1, 18)}
    evidence: dict[int, list] = {n: [] for n in range(1, 18)}
    barren = 0

    for act in acts:
        sc = act.get("sdg_scores", {}) or {}
        aligned = [n for n in range(1, 18) if (sc.get(n, sc.get(str(n), {})) or {}).get("is_aligned")]
        if not aligned:
            barren += 1
            continue
        for n in aligned:
            counts[n] += 1
            cell = sc.get(n, sc.get(str(n), {})) or {}
            evidence[n].append({
                "t": act.get("activity_text", ""),
                "s": round(float(cell.get("score", 0) or 0), 3),
                "also": [g for g in aligned if g != n],
            })

    for n in range(1, 18):
        evidence[n] = sorted(evidence[n], key=lambda e: -e["s"])[:3]

    return {
        "activities": total,
        "pages": ((a.result or {}).get("metadata", {}) or {}).get("page_count"),
        "barren": barren,
        "goals_evidenced": sum(1 for n in range(1, 18) if counts[n] > 0),
        "counts": {str(n): counts[n] for n in range(1, 18)},
        "means": {str(n): round(float(means_raw.get(n, means_raw.get(str(n), 0)) or 0), 3) for n in range(1, 18)},
        "evidence": {str(n): evidence[n] for n in range(1, 18) if evidence[n]},
    }


def build_council_detail(db: Session, code: str) -> Optional[dict[str, Any]]:
    """One council's full published detail (all years, per-Goal counts/means and
    top passages). `code` is the slug from council_slug(). Returns None if no
    published report matches."""
    q = db.query(Analysis).filter(Analysis.published.is_(True), Analysis.status == "completed")
    if code.isdigit():  # exact ABS lga_code
        rows = q.filter(Analysis.lga_code == code).all()
    else:  # slug: 'state-name' — narrow by state, then match the slug
        state = code.split("-", 1)[0].upper()
        rows = [a for a in q.filter(Analysis.state == state).all() if council_slug(a) == code]
    if not rows:
        return None
    first = rows[0]
    years = {}
    for a in rows:
        years[str(a.year) if a.year else "unknown"] = _year_detail(a)
    num_years = [y for y in years if y != "unknown"]
    latest = max(num_years) if num_years else None
    return {
        "code": code,
        "lga_code": first.lga_code,
        "name": first.council_name,
        "state": first.state,
        "class": _class(first),
        "latest_year": int(latest) if latest else None,
        "years": years,
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
