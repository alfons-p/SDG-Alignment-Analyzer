"""Download buttons component for the dashboard."""

import json
from typing import Dict, Any

import pandas as pd
import streamlit as st


def render_download_buttons(results: Dict[str, Any], key_suffix: str = ""):
    """Render download buttons.

    Args:
        results: Dictionary with alignment results
        key_suffix: Optional suffix for unique widget keys (use when rendering multiple times)
    """
    st.header("💾 Download Results")

    col1, col2, col3 = st.columns(3)

    # CSV
    with col1:
        activities = results.get("activities", [])
        if activities:
            rows = []
            for activity in activities:
                row = {
                    "activity_text": activity["activity_text"],
                    "word_count": activity["word_count"],
                    "top_sdg": activity["top_sdg"],
                    "top_sdg_name": activity["top_sdg_name"],
                    "top_score": activity["top_score"],
                    "num_aligned": activity["num_aligned"]
                }
                for sdg_num in range(1, 18):
                    row[f"sdg_{sdg_num}_score"] = activity["sdg_scores"][sdg_num]["score"]
                rows.append(row)

            df = pd.DataFrame(rows)
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="sdg_alignment.csv",
                mime="text/csv",
                key=f"download_csv{key_suffix}"
            )

    # JSON
    with col2:
        json_str = json.dumps(results, indent=2, default=str)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name="sdg_alignment.json",
            mime="application/json",
            key=f"download_json{key_suffix}"
        )

    # Summary
    with col3:
        report = results.get("report_alignment", {})
        summary = f"""SDG ALIGNMENT SUMMARY
{'=' * 50}
Source: {results.get('source', 'Unknown')}
Total Activities: {report.get('total_activities', 0)}
Mean Alignment Score: {report.get('mean_alignment_score', 0):.4f}

TOP 5 SDGs:
"""
        for i, sdg in enumerate(report.get('top_sdgs', [])[:5], 1):
            summary += f"{i}. SDG {sdg['sdg']}: {sdg['name']} (score: {sdg['mean_score']:.3f})\n"

        st.download_button(
            label="📥 Download Summary",
            data=summary,
            file_name="sdg_alignment_summary.txt",
            mime="text/plain",
            key=f"download_summary{key_suffix}"
        )