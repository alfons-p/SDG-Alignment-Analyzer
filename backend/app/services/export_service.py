"""Export service — CSV/JSON generation using Reporter."""

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd


def generate_csv_bytes(results: dict[str, Any]) -> io.BytesIO:
    """Generate CSV from results, return BytesIO buffer."""
    activities = results.get("activities", [])
    rows = []
    for activity in activities:
        row = {
            "activity_text": activity["activity_text"],
            "word_count": activity["word_count"],
            "section_type": activity.get("section_type", "general"),
            "relevance_score": activity.get("relevance_score", 0),
            "top_sdg": activity["top_sdg"],
            "top_sdg_name": activity["top_sdg_name"],
            "top_score": activity["top_score"],
            "num_aligned": activity["num_aligned"],
        }
        sdg_scores = activity["sdg_scores"]
        for sdg_num in range(1, 18):
            score = sdg_scores.get(sdg_num, sdg_scores.get(str(sdg_num), {})).get("score", 0)
            row[f"SDG_{sdg_num}_score"] = round(score, 4)
        rows.append(row)

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


def generate_json_bytes(results: dict[str, Any]) -> io.BytesIO:
    """Generate JSON from results, return BytesIO buffer."""
    buf = io.BytesIO()
    buf.write(json.dumps(results, indent=2, default=str).encode("utf-8"))
    buf.seek(0)
    return buf
