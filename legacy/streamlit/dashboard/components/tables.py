"""Activities table component for the dashboard."""

from typing import Dict, Any

import pandas as pd
import streamlit as st


def render_activities_table(results: Dict[str, Any]):
    """Render activities table.

    Args:
        results: Dictionary with alignment results
    """
    activities = results.get("activities", [])

    st.header("📋 Activity Details")

    if not activities:
        st.warning("No activities to display")
        return

    # Prepare data - show full texts when double clicked
    df_data = []
    full_texts = []  # Store full texts in order
    for activity in activities:
        full_text = activity["activity_text"]
        # full_texts.append(full_text)
        # display_text = full_text[:200] + "..." if len(full_text) > 200 else full_text
        display_text = full_text
        df_data.append({
            "Activity": display_text,
            "Top SDG": f"SDG {activity['top_sdg']}: {activity['top_sdg_name']}",
            "Score": activity["top_score"],
            "Aligned SDGs": activity["num_aligned"],
            "Words": activity["word_count"],
            "Section": activity.get("section_type", "general")
        })

    df = pd.DataFrame(df_data)
    # Keep track of original indices
    df['_original_idx'] = df.index

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        min_score = st.slider("Min Score", 0.0, 1.0, 0.0, 0.05)
    with col2:
        sdg_filter = st.multiselect(
            "Filter by Top SDG",
            options=[f"SDG {i}" for i in range(1, 18)],
            default=[]
        )
    with col3:
        section_filter = st.multiselect(
            "Filter by Section",
            options=df["Section"].unique().tolist() if "Section" in df.columns else [],
            default=[]
        )

    # Apply filters
    filtered = df[df["Score"] >= min_score].copy()
    if sdg_filter:
        filtered = filtered[filtered["Top SDG"].str.contains('|'.join(sdg_filter))]
    if section_filter:
        filtered = filtered[filtered["Section"].isin(section_filter)]

    # Configure column settings
    column_config = {
        "Activity": st.column_config.TextColumn(
            "Activity",
            width="large",
        ),
        "Score": st.column_config.ProgressColumn(
            "Score",
            format="%.3f",
            min_value=0,
            max_value=1,
        ),
        "Words": st.column_config.NumberColumn(
            "Words",
            format="%d",
        ),
        "Aligned SDGs": st.column_config.NumberColumn(
            "Aligned SDGs",
            format="%d",
        ),
    }

    # Display table (without selection for now)
    st.dataframe(
        filtered,
        use_container_width=True,
        height=350,
        column_config=column_config,
        hide_index=True,
        key="activity_table_display"
    )
