"""Overview and gaps components for the dashboard."""

from typing import Dict, Any

import streamlit as st

from src.dashboard.utils import SDG_COLORS

# Swinburne-inspired theme colors
THEME = {
    "primary": "#E03C31",
    "primary_light": "#f44a44",
    "accent": "#E03C31",
    "text": "#1e293b",
    "text_light": "#64748b",
    "border": "#e2e8f0",
}


def render_overview(results: Dict[str, Any]):
    """Render overview metrics.

    Args:
        results: Dictionary with alignment results
    """
    report = results.get("report_alignment", {})

    # Custom styled metrics
    st.markdown(f"""
    <style>
        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            border: 1px solid {THEME['border']};
            text-align: center;
            transition: all 0.3s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            font-size: 0.85rem;
            color: {THEME['text_light']};
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {THEME['primary']};
        }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Analysis Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = report.get("total_activities", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Activities</div>
            <div class="metric-value">{total:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        mean_score = report.get("mean_alignment_score", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Mean Alignment Score</div>
            <div class="metric-value">{mean_score:.3f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        top_sdgs = report.get("top_sdgs", [])
        num_aligned = sum(1 for s in top_sdgs if s["mean_score"] > 0.3)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">SDGs with Alignment</div>
            <div class="metric-value">{num_aligned}/17</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        gaps = report.get("gaps", [])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">SDG Gaps</div>
            <div class="metric-value">{len(gaps)}</div>
        </div>
        """, unsafe_allow_html=True)


def render_gaps(results: Dict[str, Any]):
    """Render SDG gaps section.

    Args:
        results: Dictionary with alignment results
    """
    report = results.get("report_alignment", {})
    gaps = report.get("gaps", [])

    st.markdown("### ⚠️ SDG Gaps")

    if not gaps:
        st.success("✓ No significant gaps detected - all SDGs have some alignment!")
        return

    st.caption("These SDGs show little to no alignment in your activities:")

    cols = st.columns(3)
    for i, gap in enumerate(gaps):
        with cols[i % 3]:
            color = SDG_COLORS.get(gap['sdg'], '#333')
            st.markdown(f"""
            <div style="background: white; border: 2px solid {color}; border-radius: 12px;
                        padding: 1rem; margin-bottom: 0.75rem; box-shadow: 0 4px 15px rgba(0,0,0,0.06);">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                    <span style="font-size: 1.5rem; font-weight: 800; color: {color}; opacity: 0.7;">
                        {gap['sdg']:02d}
                    </span>
                    <span style="font-weight: 600; color: {color};">{gap['name']}</span>
                </div>
                <div style="font-size: 0.85rem; color: #64748b;">
                    Alignment Score: <strong>{gap['mean_score']:.3f}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)