"""SDG Mentions component for the dashboard.

Extracts SDG mention rendering logic to avoid duplication between
single-file and multi-file views.
"""

import pandas as pd
import streamlit as st


def render_sdg_mentions_tab(all_results: list, sdg_mention_results: dict) -> None:
    """Render the SDG Mentions tab for multi-file view.

    Args:
        all_results: List of all analysis results
        sdg_mention_results: Dict mapping filename to SDG mention data
    """
    st.subheader("🔍 SDG Mentions")
    st.caption("Search for 'SDG' and 'sustainable development goal' in reports")

    if not sdg_mention_results:
        st.info("No SDG mention data available")
        return

    # Create dataframe from results
    rows = []
    for filename, data in sdg_mention_results.items():
        rows.append({
            'council_name': data.get('council_name', ''),
            'state': data.get('state', ''),
            'year': data.get('year', ''),
            'urban_rural': data.get('urban_rural', ''),
            'sdg': data.get('sdg', 0),
            'susdevgoal': data.get('susdevgoal', 0),
        })

    df = pd.DataFrame(rows)

    # Show summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Reports", len(df))
    with col2:
        st.metric("Reports with 'SDG'", df['sdg'].sum())
    with col3:
        st.metric("Reports with 'sustainable development goal'", df['susdevgoal'].sum())

    # Show the table
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Show details for reports with mentions
    st.markdown("### Details")

    # Filter to reports with SDG or susdevgoal mentions
    mentions_df = df[(df['sdg'] == 1) | (df['susdevgoal'] == 1)]

    if not mentions_df.empty:
        for idx, row in mentions_df.iterrows():
            filename = rows[idx]['council_name']
            with st.expander(f"📄 {filename} ({row['state']} - {row['year']})"):
                # Get full data from original results
                original_data = sdg_mention_results.get(list(sdg_mention_results.keys())[idx], {})

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**SDG (uppercase):**")
                    if original_data.get('sdg') == 1:
                        st.success("Found")
                        sdg_text = original_data.get('sdgtext', '')
                        if sdg_text:
                            st.text_area("sdgtext", sdg_text, height=150, key=f"sdg_{idx}")
                    else:
                        st.warning("Not found")

                with col_b:
                    st.markdown("**sustainable development goal:**")
                    if original_data.get('susdevgoal') == 1:
                        st.success("Found")
                        susdev_text = original_data.get('sdgfulltext', '')
                        if susdev_text:
                            st.text_area("sdgfulltext", susdev_text, height=150, key=f"susdev_{idx}")
                    else:
                        st.warning("Not found")
    else:
        st.info("No SDG mentions found in any report")


def render_single_report_sdg_mentions(results: dict, sdg_mention_results: dict) -> None:
    """Render the SDG Mentions tab for single-file view.

    Args:
        results: Analysis results for the single file
        sdg_mention_results: Dict mapping filename to SDG mention data
    """
    st.subheader("🔍 SDG Mentions")
    st.caption("Search for 'SDG' and 'sustainable development goal' in this report")

    # Get current file's SDG mention result
    current_file_name = results.get('source', '').split('/')[-1] if results.get('source') else ''

    # Find matching result
    current_mention = None
    for filename, data in sdg_mention_results.items():
        if filename == current_file_name or filename in current_file_name:
            current_mention = data
            break

    if current_mention:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Contains 'SDG'", "Yes" if current_mention.get('sdg') == 1 else "No")
            if current_mention.get('sdg') == 1:
                sdg_text = current_mention.get('sdgtext', '')
                if sdg_text:
                    st.text_area("sdgtext", sdg_text, height=200)

        with col2:
            st.metric("Contains 'sustainable development goal'", "Yes" if current_mention.get('susdevgoal') == 1 else "No")
            if current_mention.get('susdevgoal') == 1:
                susdev_text = current_mention.get('sdgfulltext', '')
                if susdev_text:
                    st.text_area("sdgfulltext", susdev_text, height=200)
    else:
        st.info("No SDG mention data available for this report")
