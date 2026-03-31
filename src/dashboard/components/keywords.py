"""SDG keyword analysis component for the dashboard."""

from typing import Dict, Any, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils import SDG_COLORS, get_chart_theme_colors
from src.dashboard.caching import get_cached_sdg_ref


def render_sdg_keyword_analysis(results_list: List[Dict[str, Any]]):
    """Render SDG keyword analysis.

    Args:
        results_list: List of alignment result dictionaries
    """
    # Get theme-aware colors
    c = get_chart_theme_colors()

    st.header("🔑 SDG Keyword Analysis")

    if not results_list:
        st.info("Process reports to see keyword analysis")
        return

    # Initialize reporter
    from src.reports import Reporter
    reporter = Reporter()

    # Settings
    col1, col2 = st.columns(2)
    with col1:
        min_score = st.slider(
            "Min Score for Keyword Extraction",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="Only extract keywords from activities with score >= this threshold"
        )
    with col2:
        top_n = st.number_input(
            "Top N Keywords",
            min_value=10,
            max_value=100,
            value=30,
            help="Number of top keywords to show per SDG"
        )

    if st.button("🔍 Analyze Keywords", type="primary"):
        with st.spinner("Extracting keywords from aligned activities..."):
            try:
                # Extract keywords
                keyword_results = reporter.analyze_sdg_keywords(
                    results_list,
                    min_score=min_score,
                    top_n=top_n
                )

                keywords = keyword_results['keywords']

                # Display keywords by SDG
                st.subheader("Top Keywords by SDG")

                for sdg_num in range(1, 18):
                    sdg_keywords = keywords.get(sdg_num, [])
                    if sdg_keywords:
                        with st.expander(f"SDG {sdg_num}: {sdg_keywords[:5] if sdg_keywords else 'No keywords'}"):
                            if sdg_keywords:
                                # Create bar chart for keywords
                                kws = [k[0] for k in sdg_keywords[:15]]
                                counts = [k[1] for k in sdg_keywords[:15]]

                                fig = go.Figure(data=[
                                    go.Bar(
                                        x=counts,
                                        y=kws,
                                        orientation='h',
                                        marker_color=SDG_COLORS.get(sdg_num, '#333')
                                    )
                                ])
                                fig.update_layout(
                                    title=f"Top Keywords for SDG {sdg_num}",
                                    xaxis=dict(
                                        title="Frequency",
                                        titlefont=dict(color=c['text']),
                                        tickfont=dict(color=c['text']),
                                        gridcolor=c['grid']
                                    ),
                                    yaxis=dict(
                                        title="Keyword",
                                        titlefont=dict(color=c['text']),
                                        tickfont=dict(color=c['text']),
                                        gridcolor=c['grid']
                                    ),
                                    height=400,
                                    paper_bgcolor=c['paper_bg'],
                                    plot_bgcolor=c['paper_bg'],
                                    title_font=dict(color=c['text'])
                                )
                                fig.update_yaxes(autorange="reversed")
                                st.plotly_chart(fig, use_container_width=True, theme=None)

                                # Show table
                                df_data = [
                                    {'Rank': i+1, 'Keyword': k[0], 'Count': k[1]}
                                    for i, k in enumerate(sdg_keywords[:top_n])
                                ]
                                st.dataframe(pd.DataFrame(df_data), use_container_width=True)

                # Download options
                st.markdown("---")
                col_dl1, col_dl2 = st.columns(2)

                with col_dl1:
                    # Create CSV of all keywords
                    all_keywords = []
                    for sdg_num in range(1, 18):
                        sdg_name = get_cached_sdg_ref().get_sdg_name(sdg_num)
                        for rank, (kw, count) in enumerate(keywords.get(sdg_num, []), 1):
                            all_keywords.append({
                                'SDG': sdg_num,
                                'SDG_Name': sdg_name,
                                'Rank': rank,
                                'Keyword': kw,
                                'Count': count
                            })

                    if all_keywords:
                        df_all = pd.DataFrame(all_keywords)
                        csv = df_all.to_csv(index=False)
                        st.download_button(
                            label="📥 Download All Keywords (CSV)",
                            data=csv,
                            file_name="sdg_keywords.csv",
                            mime="text/csv"
                        )

            except Exception as e:
                st.error(f"Error analyzing keywords: {e}")
                import traceback
                st.code(traceback.format_exc())