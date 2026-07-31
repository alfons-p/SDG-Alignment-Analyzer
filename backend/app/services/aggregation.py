"""Standalone aggregation functions — extracted logic, no Reporter dependency."""

from typing import Any

import numpy as np


def compute_report_alignment(results: dict[str, Any]) -> dict[str, Any]:
    """Return report_alignment block from results."""
    report = results.get("report_alignment", {})
    if not report:
        activities = results.get("activities", [])
        if not activities:
            return {"total_activities": 0, "mean_alignment_score": 0.0}
        report = _compute_from_activities(activities)
    return report


def _compute_from_activities(activities: list[dict]) -> dict[str, Any]:
    """Compute report_alignment from raw activities."""
    from src.config.sdg_definitions import SDG_DEFINITIONS

    if not activities:
        return {"total_activities": 0, "mean_alignment_score": 0.0}

    mean_scores = {}
    coverage = {}
    for sdg_num in range(1, 18):
        scores = [
            a["sdg_scores"].get(sdg_num, a["sdg_scores"].get(str(sdg_num), {})).get("score", 0)
            for a in activities
        ]
        mean_scores[sdg_num] = float(np.mean(scores)) if scores else 0.0
        aligned = sum(
            1 for a in activities
            if a["sdg_scores"].get(sdg_num, a["sdg_scores"].get(str(sdg_num), {})).get("is_aligned", False)
        )
        coverage[sdg_num] = aligned / len(activities) if activities else 0.0

    mean_alignment = float(np.mean([a["top_score"] for a in activities]))

    sdg_scores = sorted(
        [
            {"sdg": n, "name": SDG_DEFINITIONS[n]["name"], "mean_score": mean_scores[n], "coverage": coverage[n]}
            for n in range(1, 18)
        ],
        key=lambda x: x["mean_score"],
        reverse=True,
    )

    # A gap is a Goal with no aligned activity (coverage == 0), ranked by mean
    # score so the "nearly there" Goals lead (data-contract C#3). This differs
    # from the old mean_score==0 test, which almost never fires.
    gaps = sorted(
        [s for s in sdg_scores if s["coverage"] == 0],
        key=lambda x: x["mean_score"],
        reverse=True,
    )

    return {
        "total_activities": len(activities),
        "mean_alignment_score": mean_alignment,
        "mean_scores": mean_scores,
        "coverage": coverage,
        "top_sdgs": sdg_scores[:10],
        "gaps": gaps,
    }


def compute_multi_report_comparison(results_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build comparison rows for multiple reports. Includes per-goal `coverage`
    (all 17) so the comparison matrix can compare coverage and derive shares —
    without it the screen has only mean scores (data-contract C#4)."""
    rows = []
    for r in results_list:
        ra = r.get("report_alignment", {})
        coverage = ra.get("coverage", {}) or {}
        rows.append(
            {
                "source": r.get("source", "Unknown"),
                "total_activities": ra.get("total_activities", 0),
                "mean_alignment_score": ra.get("mean_alignment_score", 0.0),
                "mean_scores": {int(k): v for k, v in ra.get("mean_scores", {}).items()},
                "coverage": {int(k): v for k, v in coverage.items()},
                "top_sdgs": ra.get("top_sdgs", [])[:5],
            }
        )
    return rows
