"""Comparison components for the dashboard."""

from typing import Dict, Any, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils import SDG_COLORS, SDG_DATA, get_chart_theme_colors


def render_side_by_side_comparison(results_list: List[Dict[str, Any]]):
    """Render side-by-side comparison for exactly 2 reports.

    Args:
        results_list: List of alignment result dictionaries
    """
    # Get theme-aware colors
    c = get_chart_theme_colors()

    st.header("🔄 Side-by-Side Comparison")

    if len(results_list) < 2:
        st.info("Upload at least 2 files to use side-by-side comparison")
        return

    # Limit to max 2 reports for this view
    if len(results_list) > 2:
        st.warning("Side-by-side comparison works best with 2 reports. Please select 2 reports below.")

    # Get report names
    report_names = [r.get('source', f'Report {i+1}').split('/')[-1] for i, r in enumerate(results_list)]

    # Select reports to compare
    col1, col2 = st.columns(2)
    with col1:
        idx1 = st.selectbox(
            "Select First Report",
            range(len(results_list)),
            format_func=lambda i: report_names[i],
            key="sbs_report_1"
        )
    with col2:
        # Default to second report if available
        default_idx = 1 if len(results_list) > 1 else 0
        idx2 = st.selectbox(
            "Select Second Report",
            range(len(results_list)),
            index=default_idx,
            format_func=lambda i: report_names[i],
            key="sbs_report_2"
        )

    if idx1 == idx2:
        st.warning("Please select two different reports to compare")
        return

    r1 = results_list[idx1]
    r2 = results_list[idx2]

    # Overview metrics comparison
    st.subheader("Overview Metrics")
    col1, col2, col3 = st.columns(3)

    report1 = r1.get('report_alignment', {})
    report2 = r2.get('report_alignment', {})

    with col1:
        st.metric(
            "Total Activities",
            f"{report1.get('total_activities', 0)} vs {report2.get('total_activities', 0)}"
        )
    with col2:
        score1 = report1.get('mean_alignment_score', 0)
        score2 = report2.get('mean_alignment_score', 0)
        delta = score2 - score1
        st.metric(
            "Mean Alignment Score",
            f"{score1:.3f} vs {score2:.3f}",
            f"{delta:+.3f}"
        )
    with col3:
        aligned1 = sum(1 for s in report1.get('top_sdgs', []) if s['mean_score'] > 0.3)
        aligned2 = sum(1 for s in report2.get('top_sdgs', []) if s['mean_score'] > 0.3)
        st.metric(
            "SDGs with Alignment",
            f"{aligned1}/17 vs {aligned2}/17"
        )

    # Side-by-side SDG scores
    st.subheader("SDG Alignment Comparison")

    # Prepare comparison data
    mean_scores1 = report1.get('mean_scores', {})
    mean_scores2 = report2.get('mean_scores', {})

    comparison_data = []
    for sdg_num in range(1, 18):
        comparison_data.append({
            'SDG': f"SDG {sdg_num}",
            report_names[idx1]: mean_scores1.get(sdg_num, 0),
            report_names[idx2]: mean_scores2.get(sdg_num, 0)
        })

    df_compare = pd.DataFrame(comparison_data)

    # Create comparison bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=report_names[idx1],
        x=df_compare['SDG'],
        y=df_compare[report_names[idx1]],
        marker_color='#667eea'
    ))
    fig.add_trace(go.Bar(
        name=report_names[idx2],
        x=df_compare['SDG'],
        y=df_compare[report_names[idx2]],
        marker_color='#f093fb'
    ))

    fig.update_layout(
        title="SDG Alignment Scores Comparison",
        xaxis=dict(
            title=dict(text="Sustainable Development Goals", font=dict(color=c['text'])),
            tickfont=dict(color=c['text']),
            gridcolor=c['grid']
        ),
        yaxis=dict(
            title=dict(text="Mean Alignment Score", font=dict(color=c['text'])),
            range=[0, 1],
            tickfont=dict(color=c['text']),
            gridcolor=c['grid']
        ),
        barmode='group',
        height=500,
        paper_bgcolor=c['paper_bg'],
        plot_bgcolor=c['paper_bg'],
        legend=dict(
            font=dict(color=c['text']),
            bgcolor=c['legend_bg']
        ),
        title_font=dict(color=c['text']),
        font=dict(color=c['text'])
    )

    st.plotly_chart(fig, use_container_width=True, theme=None)

    # Top 5 SDGs for each report
    st.subheader("Top 5 SDGs by Report")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{report_names[idx1]}**")
        top_sdgs1 = report1.get('top_sdgs', [])[:5]
        for sdg in top_sdgs1:
            color = SDG_COLORS.get(sdg['sdg'], '#333')
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding-left: 10px; margin-bottom: 8px;">
                <strong>SDG {sdg['sdg']}: {sdg['name']}</strong><br>
                Score: {sdg['mean_score']:.3f} | Coverage: {sdg['coverage']*100:.1f}%
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"**{report_names[idx2]}**")
        top_sdgs2 = report2.get('top_sdgs', [])[:5]
        for sdg in top_sdgs2:
            color = SDG_COLORS.get(sdg['sdg'], '#333')
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding-left: 10px; margin-bottom: 8px;">
                <strong>SDG {sdg['sdg']}: {sdg['name']}</strong><br>
                Score: {sdg['mean_score']:.3f} | Coverage: {sdg['coverage']*100:.1f}%
            </div>
            """, unsafe_allow_html=True)

    # SDG Gaps comparison
    st.subheader("SDG Gaps Comparison")
    gaps1 = report1.get('gaps', [])
    gaps2 = report2.get('gaps', [])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{report_names[idx1]} - Gaps ({len(gaps1)} SDGs)**")
        if gaps1:
            for gap in gaps1:
                color = SDG_COLORS.get(gap['sdg'], '#333')
                st.markdown(f"""
                <div style="border: 2px solid {color}; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
                    <strong style="color: {color};">SDG {gap['sdg']}</strong>: {gap['name']}<br>
                    <span style="font-size: 0.8rem;">Score: {gap['mean_score']:.3f}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✓ No significant gaps")

    with col2:
        st.markdown(f"**{report_names[idx2]} - Gaps ({len(gaps2)} SDGs)**")
        if gaps2:
            for gap in gaps2:
                color = SDG_COLORS.get(gap['sdg'], '#333')
                st.markdown(f"""
                <div style="border: 2px solid {color}; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
                    <strong style="color: {color};">SDG {gap['sdg']}</strong>: {gap['name']}<br>
                    <span style="font-size: 0.8rem;">Score: {gap['mean_score']:.3f}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✓ No significant gaps")

    # Summary comparison table
    st.subheader("Summary Comparison Table")
    summary_rows = []
    for sdg_num in range(1, 18):
        score1 = mean_scores1.get(sdg_num, 0)
        score2 = mean_scores2.get(sdg_num, 0)
        sdg_name = SDG_DATA[sdg_num]['name']
        diff = score2 - score1

        summary_rows.append({
            'SDG': f"SDG {sdg_num}",
            'Name': sdg_name,
            report_names[idx1]: f"{score1:.3f}",
            report_names[idx2]: f"{score2:.3f}",
            'Difference': f"{diff:+.3f}",
            'Winner': report_names[idx1] if score1 > score2 else report_names[idx2] if score2 > score1 else "Tie"
        })

    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True)

    # Download comparison
    csv = df_summary.to_csv(index=False)
    st.download_button(
        label="📥 Download Comparison (CSV)",
        data=csv,
        file_name="side_by_side_comparison.csv",
        mime="text/csv"
    )


def render_multi_report_comparison(results_list: List[Dict[str, Any]], threshold: float = 0.3):
    """Render multi-report comparison visualizations.

    Args:
        results_list: List of alignment result dictionaries
        threshold: Minimum threshold for alignment (unused but kept for API compatibility)
    """
    # Get theme-aware colors
    c = get_chart_theme_colors()

    st.header("📊 Multi-Report Comparison")

    if len(results_list) < 2:
        st.info("Upload multiple files to see comparison analysis")
        return

    # Initialize reporter for visualizations
    from src.reports import Reporter
    reporter = Reporter()

    # Create tabs for different comparisons
    comp_tab1, comp_tab2, comp_tab3 = st.tabs([
        "📈 Alignment Comparison", "📊 Coverage Comparison", "📋 Summary Table"
    ])

    with comp_tab1:
        st.subheader("SDG Alignment Comparison Across Reports")

        # Prepare data for comparison
        comparison_data = []
        for result in results_list:
            source = result.get('source', 'Unknown')
            report = result.get('report_alignment', {})
            mean_scores = report.get('mean_scores', {})

            for sdg_num in range(1, 18):
                comparison_data.append({
                    'Report': source.split('/')[-1] if '/' in source else source,
                    'SDG': f"SDG {sdg_num}",
                    'Score': mean_scores.get(sdg_num, 0),
                    'sdg_num': sdg_num
                })

        if comparison_data:
            df = pd.DataFrame(comparison_data)

            # Create grouped bar chart
            fig = px.bar(
                df,
                x='SDG',
                y='Score',
                color='Report',
                barmode='group',
                title="Mean SDG Alignment Scores by Report",
                labels={'Score': 'Mean Alignment Score', 'SDG': 'Sustainable Development Goal'},
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            fig.update_layout(
                height=500,
                paper_bgcolor=c['paper_bg'],
                plot_bgcolor=c['paper_bg'],
                title_font=dict(color=c['text']),
                xaxis=dict(
                    title=dict(font=dict(color=c['text'])),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                yaxis=dict(
                    title=dict(font=dict(color=c['text'])),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                legend=dict(font=dict(color=c['text']), bgcolor=c['legend_bg'])
            )
            st.plotly_chart(fig, use_container_width=True, theme=None)

            # Create box plot
            fig2 = px.box(
                df,
                x='SDG',
                y='Score',
                title="SDG Score Distribution Across Reports",
                labels={'Score': 'Alignment Score', 'SDG': 'SDG'},
                color_discrete_sequence=['#667eea']
            )
            fig2.update_layout(
                height=400,
                paper_bgcolor=c['paper_bg'],
                plot_bgcolor=c['paper_bg'],
                title_font=dict(color=c['text']),
                xaxis=dict(
                    title=dict(font=dict(color=c['text'])),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                yaxis=dict(
                    title=dict(font=dict(color=c['text'])),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                )
            )
            st.plotly_chart(fig2, use_container_width=True, theme=None)

    with comp_tab2:
        st.subheader("SDG Coverage Comparison")
        st.markdown("Shows what percentage of activities are aligned with each SDG across reports.")

        coverage_data = []
        for result in results_list:
            source = result.get('source', 'Unknown')
            report = result.get('report_alignment', {})
            top_sdgs = {s['sdg']: s for s in report.get('top_sdgs', [])}

            for sdg_num in range(1, 18):
                sdg_data = top_sdgs.get(sdg_num, {'coverage': 0})
                coverage_data.append({
                    'Report': source.split('/')[-1] if '/' in source else source,
                    'SDG': f"SDG {sdg_num}",
                    'Coverage %': sdg_data.get('coverage', 0) * 100,
                    'sdg_num': sdg_num
                })

        if coverage_data:
            df_cov = pd.DataFrame(coverage_data)

            fig = px.bar(
                df_cov,
                x='SDG',
                y='Coverage %',
                color='Report',
                barmode='group',
                title="SDG Coverage (% of Activities Aligned)",
                labels={'Coverage %': 'Coverage Percentage', 'SDG': 'SDG'},
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(
                height=500,
                paper_bgcolor=c['paper_bg'],
                plot_bgcolor=c['paper_bg'],
                title_font=dict(color=c['text']),
                xaxis=dict(
                    title=dict(font=dict(color=c['text'])),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                yaxis=dict(
                    title=dict(font=dict(color=c['text'])),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                legend=dict(font=dict(color=c['text']), bgcolor=c['legend_bg'])
            )
            st.plotly_chart(fig, use_container_width=True, theme=None)

    with comp_tab3:
        st.subheader("Alignment Summary Table")

        try:
            summary_df = reporter.create_alignment_summary(results_list)
            if not summary_df.empty:
                st.dataframe(summary_df, use_container_width=True)

                # Download button for summary
                csv = summary_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Summary CSV",
                    data=csv,
                    file_name="alignment_summary.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Could not create summary: {e}")