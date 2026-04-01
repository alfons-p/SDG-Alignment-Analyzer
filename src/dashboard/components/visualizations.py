"""Visualization components for the dashboard."""

from typing import Dict, Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils import SDG_COLORS, get_chart_theme_colors


def render_top_sdgs(results: Dict[str, Any]):
    """Render top SDGs section.

    Args:
        results: Dictionary with alignment results
    """
    report = results.get("report_alignment", {})
    top_sdgs = report.get("top_sdgs", [])[:10]

    # Get theme-aware colors
    c = get_chart_theme_colors()

    st.markdown("### 🏆 Top SDGs by Alignment")

    if not top_sdgs:
        st.warning("No SDG alignment data available")
        return

    # Create bar chart
    df = pd.DataFrame([
        {
            "SDG": f"SDG {s['sdg']}",
            "Name": s['name'],
            "Score": s['mean_score'],
            "Coverage": s['coverage'] * 100,
            "sdg_num": s['sdg']
        }
        for s in top_sdgs
    ])

    df['Color'] = df['sdg_num'].map(SDG_COLORS)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            df,
            x="Score",
            y="SDG",
            color="SDG",
            color_discrete_map={f"SDG {i}": SDG_COLORS[i] for i in range(1, 18)},
            orientation='h',
            title="SDG Alignment Scores",
            labels={"Score": "Mean Alignment Score", "SDG": ""},
            text=df["Score"].apply(lambda x: f"{x:.3f}")
        )
        fig.update_traces(
            textposition='outside',
            textfont=dict(color=c['text'])
        )
        fig.update_layout(
            showlegend=False,
            height=400,
            paper_bgcolor=c['paper_bg'],
            plot_bgcolor=c['paper_bg'],
            title_font=dict(color=c['text'], size=18, family="Inter"),
            xaxis=dict(
                title=dict(font=dict(color=c['text'])),
                tickfont=dict(color=c['text']),
                gridcolor=c['grid']
            ),
            yaxis=dict(
                tickfont=dict(color=c['text'], size=11),
                gridcolor=c['grid']
            ),
            font=dict(color=c['text'], family="Inter"),
            margin=dict(l=100, r=40, t=60, b=40)
        )
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with col2:
        st.markdown("#### SDG Details")
        for sdg in top_sdgs[:5]:
            color = SDG_COLORS.get(sdg['sdg'], '#333')
            st.markdown(f"""
            <div style="background: white; border-left: 4px solid {color}; border-radius: 0 8px 8px 0;
                        padding: 0.75rem; margin-bottom: 0.75rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-weight: 600; color: {color}; font-size: 0.95rem;">
                    SDG {sdg['sdg']}: {sdg['name']}
                </div>
                <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.25rem;">
                    Score: <strong>{sdg['mean_score']:.3f}</strong> |
                    Coverage: {sdg['coverage']*100:.1f}%
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_radar_chart(results: Dict[str, Any], all_results: list = None):
    """Render radar chart showing SDG Coverage % or Alignment Score.

    Args:
        results: Dictionary with alignment results (single report)
        all_results: Optional list of all results for multi-report comparison
    """
    # Get theme-aware colors
    c = get_chart_theme_colors()

    # Initialize zoom level in session state
    if "radar_zoom" not in st.session_state:
        st.session_state.radar_zoom = 1.0

    # Check if showing all reports
    show_all = all_results is not None and len(all_results) > 1

    # Radio button to select metric
    metric_option = st.radio(
        "Select metric:",
        ["Coverage %", "Average Score"],
        horizontal=True,
        help="Coverage: % of activities aligned | Score: Mean alignment score"
    )

    if show_all:
        # Multiple reports - show all on one chart
        st.markdown("### 🎯 SDG Coverage Profile - All Reports")

        # Extract file names
        file_names = []
        for r in all_results:
            source = r.get('source', 'Unknown')
            file_names.append(source.split('/')[-1] if '/' in source else source)

        # Colors for different reports
        colors = ['#E03C31', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

        fig = go.Figure()

        # Calculate max value across all reports for auto-scaling
        all_values = []
        for idx, (result, name) in enumerate(zip(all_results, file_names)):
            report = result.get("report_alignment", {})
            coverage = report.get("coverage", {})
            values = [coverage.get(i, 0) * 100 for i in range(1, 18)]
            all_values.extend(values)

        max_val = max(all_values) if all_values else 100
        # Add 10% padding but cap at 100%
        max_val = min(max_val * 1.1, 100)
        # Apply zoom level (dividing by zoom factor to show smaller range)
        zoomed_max = max_val / st.session_state.radar_zoom

        for idx, (result, name) in enumerate(zip(all_results, file_names)):
            report = result.get("report_alignment", {})
            coverage = report.get("coverage", {})
            categories = [f"SDG {i}" for i in range(1, 18)]
            values = [coverage.get(i, 0) * 100 for i in range(1, 18)]

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself' if idx == 0 else 'none',
                fillcolor=f'rgba(224, 60, 49, 0.1)',
                line=dict(color=colors[idx % len(colors)], width=2),
                name=name[:20],  # Truncate long names
                hovertemplate='%{theta}: %{r:.1f}%<extra></extra>'
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, zoomed_max],
                    tickfont=dict(size=10, color=c['text']),
                    ticksuffix='%',
                    gridcolor=c['grid'],
                    linecolor=c['grid']
                ),
                angularaxis=dict(
                    tickfont=dict(size=9, color=c['text']),
                    gridcolor=c['grid']
                ),
                bgcolor=c['background']
            ),
            paper_bgcolor=c['paper_bg'],
            plot_bgcolor=c['paper_bg'],
            showlegend=True,
            height=500,
            margin=dict(l=80, r=80, t=40, b=40),
            font=dict(color=c['text'], family="Inter"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )

        st.plotly_chart(fig, use_container_width=True, theme=None)

        # Zoom controls below chart
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🔍 Zoom In", key="zoom_in_multi", use_container_width=True):
                st.session_state.radar_zoom = min(st.session_state.radar_zoom + 0.25, 3.0)
        with col2:
            if st.button("🔍 Zoom Out", key="zoom_out_multi", use_container_width=True):
                st.session_state.radar_zoom = max(st.session_state.radar_zoom - 0.25, 0.5)
        with col3:
            st.caption(f"Zoom: {st.session_state.radar_zoom:.2f}x | Max: {max_val:.1f}%")

        return  # Exit early for multi-report view

    # Single report view (original code)
    report = results.get("report_alignment", {})
    coverage = report.get("coverage", {})
    top_sdgs = report.get("top_sdgs", [])

    # Build sdg_scores dict from top_sdgs for Average Score metric
    sdg_scores = {s['sdg']: s['mean_score'] for s in top_sdgs}

    if metric_option == "Coverage %":
        st.markdown("### 🎯 SDG Coverage Profile")
        st.caption("Percentage of activities aligned with each SDG (changes with threshold)")
        categories = [f"SDG {i}" for i in range(1, 18)]
        values = [coverage.get(i, 0) * 100 for i in range(1, 18)]
        max_val = max(values) * 1.05 if max(values) > 0 else 100  # 5% padding above max data
        max_val = min(max_val, 100)  # Cap at 100%
        unit = "%"
        fill_color = 'rgba(224, 60, 49, 0.25)'
        line_color = '#E03C31'
    else:
        st.markdown("### 🎯 SDG Average Alignment Score")
        st.caption("Mean alignment score for each SDG (changes with threshold)")
        categories = [f"SDG {i}" for i in range(1, 18)]
        values = [sdg_scores.get(i, 0) for i in range(1, 18)]
        max_val = max(values) * 1.05 if max(values) > 0 else 1.0  # 5% padding above max data
        max_val = min(max_val, 1.0)  # Cap at 1.0
        unit = ""
        fill_color = 'rgba(59, 130, 246, 0.25)'
        line_color = '#3b82f6'

    # Calculate zoomed range
    zoomed_max = max_val / st.session_state.radar_zoom

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor=fill_color,
        line=dict(color=line_color, width=3),
        name=metric_option,
        hovertemplate=f'%{{theta}}: %{{r:.1f}}{unit}<extra></extra>'
    ))

    fig.update_layout(
        dragmode='zoom',
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, zoomed_max],
                tickfont=dict(size=10, color=c['text']),
                ticksuffix=unit,
                gridcolor=c['grid'],
                linecolor=c['grid']
            ),
            angularaxis=dict(
                tickfont=dict(size=9, color=c['text']),
                gridcolor=c['grid']
            ),
            bgcolor=c['background']
        ),
        paper_bgcolor=c['paper_bg'],
        plot_bgcolor=c['paper_bg'],
        showlegend=False,
        height=500,
        margin=dict(l=80, r=80, t=40, b=40),
        font=dict(color=c['text'], family="Inter")
    )

    st.plotly_chart(fig, use_container_width=True, theme=None)

    # Zoom controls below the chart
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔍 Zoom In", key="zoom_in", use_container_width=True):
            st.session_state.radar_zoom = min(st.session_state.radar_zoom + 0.25, 3.0)
    with col2:
        if st.button("🔍 Zoom Out", key="zoom_out", use_container_width=True):
            st.session_state.radar_zoom = max(st.session_state.radar_zoom - 0.25, 0.5)
    with col3:
        st.caption(f"Zoom: {st.session_state.radar_zoom:.2f}x (range 0.5x - 3x)")


def render_heatmap(results: Dict[str, Any]):
    """Render activity-SDG heatmap.

    Args:
        results: Dictionary with alignment results
    """
    activities = results.get("activities", [])

    # Get theme-aware colors
    c = get_chart_theme_colors()

    st.markdown("### 🔥 Activity-SDG Alignment Heatmap")
    st.caption("Top 30 activities by relevance score")

    if not activities:
        st.warning("No activities to display")
        return

    # Take top 30 activities
    sorted_activities = sorted(
        activities,
        key=lambda x: x.get("relevance_score", 0),
        reverse=True
    )[:30]

    # Build matrix
    z = []
    y_labels = []

    for activity in sorted_activities:
        y_labels.append(activity["activity_text"][:80] + "...")
        row = [activity["sdg_scores"][i]["score"] for i in range(1, 18)]
        z.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[f"SDG {i}" for i in range(1, 18)],
        y=y_labels,
        colorscale='YlOrRd',
        zmin=0,
        zmax=1,
        colorbar=dict(
            title="Score",
            title=dict(font=dict(color=c['text'])),
            tickfont=dict(color=c['text'])
        ),
        hovertemplate='%{x}<br>%{y}<br>Score: %{z:.3f}<extra></extra>'
    ))

    fig.update_layout(
        xaxis=dict(
            title="Sustainable Development Goals",
            title=dict(font=dict(color=c['text'], size=12)),
            tickfont=dict(color=c['text']),
            gridcolor=c['grid']
        ),
        yaxis=dict(
            title="Activities",
            title=dict(font=dict(color=c['text'], size=14)),
            tickfont=dict(color=c['text'], size=10),
            tickangle=0,
            gridcolor=c['grid']
        ),
        paper_bgcolor=c['paper_bg'],
        plot_bgcolor=c['paper_bg'],
        height=max(600, len(sorted_activities) * 20),
        width=400,
        margin=dict(l=475, r=40, t=40, b=60),
        font=dict(color=c['text'], family="Inter")
    )

    st.plotly_chart(fig, use_container_width=True, theme=None)