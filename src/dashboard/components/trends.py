"""Trend analysis component for the dashboard.

Note: This component is not yet integrated into the main app flow.
It provides SDG trend analysis functionality for future use.
"""

import json
from typing import Dict, Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils import get_chart_theme_colors, get_trend_analyzer


def render_trend_analysis():
    """Render the trend analysis section."""
    # Get theme-aware colors
    c = get_chart_theme_colors()

    st.header("📈 SDG Trend Analysis")
    st.markdown("""
    Analyze trends in SDG alignment over time across councils and years.
    This feature compares SDG scores from multiple annual reports to identify
    increasing, decreasing, or stable trends.
    """)

    # Initialize trend analyzer
    trend_analyzer = get_trend_analyzer()

    # Sidebar options
    st.sidebar.header("Trend Analysis Options")

    trend_type = st.sidebar.radio(
        "Analysis Type",
        ["Overall Trends", "State Trends", "Council Trends"],
        help="Select which data to analyze for trends"
    )

    # Get available filter options
    available_states = trend_analyzer.get_available_states()
    available_years = trend_analyzer.get_available_years()

    st.sidebar.markdown("---")
    st.sidebar.header("📅 Filters")

    # Year filter (available for all trend types)
    if available_years:
        selected_years = st.sidebar.multiselect(
            "Filter by Year(s)",
            options=available_years,
            default=available_years,
            help="Select specific years to include in analysis"
        )
    else:
        selected_years = []

    # State filter (for Overall Trends)
    if trend_type == "Overall Trends" and available_states:
        selected_states = st.sidebar.multiselect(
            "Filter by State(s)",
            options=available_states,
            default=available_states,
            help="Select specific states to include in analysis"
        )
    else:
        selected_states = available_states if available_states else []

    results = []
    trends = {}
    title = ""

    if trend_type == "Overall Trends":
        with st.spinner("Loading trend data..."):
            # Load results with filters
            if selected_states:
                results = []
                for state in selected_states:
                    results.extend(trend_analyzer.load_council_results(state=state))
            else:
                results = trend_analyzer.load_council_results()

            # Filter by year if specified
            if selected_years:
                results = [r for r in results if r.get('metadata', {}).get('year', '') in selected_years]

            if len(selected_states) == 1:
                title = f"SDG Trends for {selected_states[0]}"
            elif selected_states:
                title = f"SDG Trends for {', '.join(selected_states)}"
            else:
                title = "Overall SDG Trends (All Councils)"

            if selected_years:
                title += f" ({', '.join(selected_years)})"

            # Compute trends from filtered results
            trends = trend_analyzer._compute_trends_from_results(results) if results else {}

    elif trend_type == "State Trends":
        if not available_states:
            st.warning("No state data found. Please process reports with state metadata.")
            return

        selected_state = st.sidebar.selectbox("Select State", available_states)
        compare_states = st.sidebar.checkbox("Compare with other states", value=False)

        with st.spinner(f"Loading trend data for {selected_state}..."):
            results = trend_analyzer.load_council_results(state=selected_state)

            # Filter by year if specified
            if selected_years:
                results = [r for r in results if r.get('metadata', {}).get('year', '') in selected_years]

            trends = trend_analyzer.analyze_state_trends(selected_state)
            title = f"SDG Trends for {selected_state}"
            if selected_years:
                title += f" ({', '.join(selected_years)})"

        # Load comparison data if requested
        comparison_trends = {}
        if compare_states and len(available_states) > 1:
            with st.spinner("Loading comparison data..."):
                comparison_trends = trend_analyzer.analyze_multiple_states(available_states)

    else:  # Council Trends
        all_results = trend_analyzer.load_council_results()
        council_names = list(set([
            r.get('source', '').split('/')[-1].replace('_alignment.json', '').replace('_', ' ')
            for r in all_results
        ]))
        council_names.sort()

        if not council_names:
            st.warning("No council data found. Please process some reports first.")
            return

        selected_council = st.sidebar.selectbox("Select Council", council_names)

        with st.spinner(f"Loading trend data for {selected_council}..."):
            trends = trend_analyzer.analyze_council_trends(selected_council)
            title = f"SDG Trends for {selected_council}"

    if not trends:
        st.warning("Insufficient data for trend analysis. Need at least 2 years of data.")
        return

    summary_df = trend_analyzer.get_trend_summary_dataframe(trends)

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Trend Visualization", "📈 Trend Metrics", "📋 Summary Table", "📥 Export"
    ])

    with tab1:
        st.subheader(title)

        # State comparison visualization
        if trend_type == "State Trends" and compare_states and comparison_trends:
            st.subheader("State Comparison")

            # Multi-state trend plot
            fig_comp = go.Figure()
            state_colors = {'NSW': '#1f77b4', 'VIC': '#ff7f0e', 'QLD': '#2ca02c',
                           'WA': '#d62728', 'SA': '#9467bd', 'TAS': '#8c564b',
                           'ACT': '#e377c2', 'NT': '#7f7f7f'}

            for state, state_trend_data in comparison_trends.items():
                for sdg_num, trend in state_trend_data.items():
                    # Only show selected SDG or all
                    fig_comp.add_trace(go.Scatter(
                        x=trend.years,
                        y=trend.scores,
                        mode='lines+markers',
                        name=f"{state} - SDG {sdg_num}",
                        line=dict(color=state_colors.get(state, '#333')),
                        visible='legendonly' if sdg_num != 1 else True
                    ))

            fig_comp.update_layout(
                title="SDG Trends Comparison Across States",
                xaxis=dict(
                    title="Year",
                    titlefont=dict(color=c['text']),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                yaxis=dict(
                    title="Mean Alignment Score",
                    range=[0, 1],
                    titlefont=dict(color=c['text']),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                hovermode='x unified',
                height=600,
                paper_bgcolor=c['paper_bg'],
                plot_bgcolor=c['paper_bg'],
                title_font=dict(color=c['text']),
                legend=dict(font=dict(color=c['text']), bgcolor=c['legend_bg'])
            )
            st.plotly_chart(fig_comp, use_container_width=True, theme=None)

            # State comparison bar chart
            st.subheader("Trend Slopes Comparison")

            comparison_data = []
            for state, state_trend_data in comparison_trends.items():
                for sdg_num, trend in state_trend_data.items():
                    comparison_data.append({
                        'State': state,
                        'SDG': sdg_num,
                        'SDG Name': trend.sdg_name,
                        'Slope': trend.trend_slope,
                        'Trend Direction': trend.trend_direction,
                        'Significant': trend.is_significant
                    })

            if comparison_data:
                comp_df = pd.DataFrame(comparison_data)

                fig_bar = px.bar(
                    comp_df,
                    x='SDG',
                    y='Slope',
                    color='State',
                    barmode='group',
                    facet_col='Trend Direction',
                    title="Trend Slopes by State and SDG",
                    labels={'Slope': 'Trend Slope', 'SDG': 'SDG Number'}
                )
                fig_bar.update_layout(
                    paper_bgcolor=c['paper_bg'],
                    plot_bgcolor=c['paper_bg'],
                    title_font=dict(color=c['text']),
                    xaxis=dict(
                        titlefont=dict(color=c['text']),
                        tickfont=dict(color=c['text']),
                        gridcolor=c['grid']
                    ),
                    yaxis=dict(
                        titlefont=dict(color=c['text']),
                        tickfont=dict(color=c['text']),
                        gridcolor=c['grid']
                    ),
                    legend=dict(font=dict(color=c['text']), bgcolor=c['legend_bg'])
                )
                st.plotly_chart(fig_bar, use_container_width=True, theme=None)

        # Individual state trends
        if trends:
            fig = trend_analyzer.create_interactive_trend_plot(trends, title=title)
            if fig:
                fig.update_layout(
                    paper_bgcolor=c['paper_bg'],
                    plot_bgcolor=c['paper_bg'],
                    title_font=dict(color=c['text']),
                    xaxis=dict(
                        titlefont=dict(color=c['text']),
                        tickfont=dict(color=c['text']),
                        gridcolor=c['grid']
                    ),
                    yaxis=dict(
                        titlefont=dict(color=c['text']),
                        tickfont=dict(color=c['text']),
                        gridcolor=c['grid']
                    ),
                    legend=dict(font=dict(color=c['text']), bgcolor=c['legend_bg'])
                )
                st.plotly_chart(fig, use_container_width=True, theme=None)

        # Bar chart of trends
        st.subheader("Trend Direction Summary")

        if not summary_df.empty:
            direction_colors = {
                'increasing': '#28a745',
                'decreasing': '#dc3545',
                'stable': '#6c757d'
            }

            fig2 = px.bar(
                summary_df,
                x='SDG',
                y='Slope',
                color='Trend Direction',
                color_discrete_map=direction_colors,
                title="Trend Slopes by SDG",
                labels={'Slope': 'Trend Slope', 'SDG': 'SDG Number'},
                hover_data=['SDG Name', 'R-squared', 'P-value', 'Percent Change']
            )
            fig2.update_layout(
                paper_bgcolor=c['paper_bg'],
                plot_bgcolor=c['paper_bg'],
                title_font=dict(color=c['text']),
                xaxis=dict(
                    titlefont=dict(color=c['text']),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                yaxis=dict(
                    titlefont=dict(color=c['text']),
                    tickfont=dict(color=c['text']),
                    gridcolor=c['grid']
                ),
                legend=dict(font=dict(color=c['text']), bgcolor=c['legend_bg'])
            )
            st.plotly_chart(fig2, use_container_width=True, theme=None)

    with tab2:
        st.subheader("Trend Metrics")

        if not summary_df.empty:
            sig_increasing = summary_df[(summary_df['Significant'] == True) &
                                        (summary_df['Trend Direction'] == 'increasing')]
            sig_decreasing = summary_df[(summary_df['Significant'] == True) &
                                        (summary_df['Trend Direction'] == 'decreasing')]
            stable = summary_df[summary_df['Trend Direction'] == 'stable']

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Significant Increases", len(sig_increasing))
            with col2:
                st.metric("Significant Decreases", len(sig_decreasing))
            with col3:
                st.metric("Stable", len(stable))

            st.markdown("---")
            st.markdown("### Top Trends by Magnitude")

            sorted_df = summary_df.copy()
            sorted_df['Abs Slope'] = sorted_df['Slope'].abs()
            sorted_df = sorted_df.sort_values('Abs Slope', ascending=False)

            for _, row in sorted_df.head(5).iterrows():
                sdg_num = int(row['SDG'])
                sig_marker = "✓" if row['Significant'] else ""

                with st.container():
                    cols = st.columns([1, 4, 2, 2])
                    with cols[0]:
                        st.markdown(f"**SDG {sdg_num}**")
                    with cols[1]:
                        st.markdown(f"{row['SDG Name']}")
                    with cols[2]:
                        direction = row['Trend Direction']
                        emoji = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}.get(direction, "")
                        st.markdown(f"{emoji} {direction.title()}")
                    with cols[3]:
                        st.markdown(f"Slope: {row['Slope']:.4f} {sig_marker}")

    with tab3:
        st.subheader("Detailed Summary Table")

        if not summary_df.empty:
            display_df = summary_df.copy()
            display_df['Significant'] = display_df['Significant'].apply(lambda x: 'Yes' if x else 'No')
            display_df['Slope'] = display_df['Slope'].round(4)
            display_df['R-squared'] = display_df['R-squared'].round(3)
            display_df['P-value'] = display_df['P-value'].round(4)
            display_df['Percent Change'] = display_df['Percent Change'].round(1)

            st.dataframe(
                display_df[['SDG', 'SDG Name', 'Trend Direction', 'Slope',
                           'R-squared', 'P-value', 'Significant', 'Percent Change']],
                use_container_width=True
            )

            st.markdown("---")
            st.markdown("### Statistical Interpretation")
            st.markdown("""
            - **Trend Direction**: Based on the slope of the linear regression
            - **Significant**: p-value < 0.05 (statistically significant trend)
            - **R-squared**: Proportion of variance explained by the trend (0-1)
            - **Slope**: Rate of change per year in alignment score
            - **Percent Change**: Total percentage change from first to last year
            """)

    with tab4:
        st.subheader("Export Trend Analysis")

        if not summary_df.empty:
            csv = summary_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Trend Summary (CSV)",
                data=csv,
                file_name=f"trend_analysis_{trend_type.replace(' ', '_').lower()}.csv",
                mime="text/csv"
            )

            def convert_to_native(obj):
                """Convert numpy types to native Python types for JSON serialization."""
                if hasattr(obj, 'item'):  # numpy scalar
                    return obj.item()
                elif isinstance(obj, dict):
                    return {k: convert_to_native(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_native(v) for v in obj]
                elif isinstance(obj, tuple):
                    return [convert_to_native(v) for v in obj]
                return obj

            trends_json = {}
            for sdg_num, trend in trends.items():
                trends_json[str(sdg_num)] = {
                    'sdg': int(trend.sdg),
                    'sdg_name': trend.sdg_name,
                    'years': list(trend.years),
                    'scores': [float(s) for s in trend.scores],
                    'trend_direction': trend.trend_direction,
                    'trend_slope': float(trend.trend_slope),
                    'r_squared': float(trend.r_squared),
                    'p_value': float(trend.p_value),
                    'percent_change': float(trend.percent_change),
                    'is_significant': bool(trend.is_significant)
                }

            json_str = json.dumps(trends_json, indent=2, default=str)
            st.download_button(
                label="📥 Download Trend Details (JSON)",
                data=json_str,
                file_name=f"trend_analysis_{trend_type.replace(' ', '_').lower()}.json",
                mime="application/json"
            )