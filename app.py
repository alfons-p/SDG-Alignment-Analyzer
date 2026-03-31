"""Streamlit Web Dashboard for SDG Alignment Analyzer.

Interactive web interface for analyzing and visualizing council annual reports.
"""

import hashlib
import logging
from pathlib import Path

import streamlit as st

# Import dashboard utilities
from src.dashboard.session import SessionManager, CacheKey
from src.dashboard.cache_manager import CacheManager

# Import styles
from src.dashboard.styles import get_landing_page_styles

# Import processing functions
from src.dashboard.processing import process_pdf, scan_sdg_mentions_cached

# Import UI components
from src.dashboard.components import (
    render_landing_page,
    render_header,
    render_sidebar_settings,
    render_overview,
    render_gaps,
    render_top_sdgs,
    render_radar_chart,
    render_heatmap,
    render_activities_table,
    render_side_by_side_comparison,
    render_multi_report_comparison,
    render_sdg_keyword_analysis,
    render_download_buttons,
    render_sdg_mentions_tab,
    render_single_report_sdg_mentions,
)

# Environment variables are loaded centrally by EnvLoader
# No need to call load_dotenv here - EnvLoader auto-loads on import

# Module-level logging
logger = logging.getLogger(__name__)

# Set up page config
st.set_page_config(
    page_title="SDG Alignment Analyzer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply CSS styles
st.markdown(get_landing_page_styles(), unsafe_allow_html=True)

# Tab definitions as constants
TABS_MULTI = ["📊 Overview", "🏆 Top SDGs", "🔥 Heatmap", "📋 Activities", "🔄 Side-by-Side", "📈 Comparison", "🔑 Keywords", "🔍 SDG Mentions", "💾 Download"]
TABS_SINGLE = ["📊 Overview", "🏆 Top SDGs", "🔥 Heatmap", "📋 Activities", "🔍 SDG Mentions", "💾 Download"]


def main():
    """Main app function."""
    # Initialize session state
    SessionManager.init()
    cache_mgr = CacheManager(SessionManager)

    render_header()

    # Sidebar: Upload and Settings
    settings = render_sidebar_settings()

    if not settings.uploaded_files:
        # Show the professional landing page
        render_landing_page()
        # Clear session state when no files uploaded
        SessionManager.clear_results()
        # Clear stale file names
        if 'processed_file_names' in st.session_state:
            del st.session_state.processed_file_names
        return

    # Compute combined file hash for cache invalidation
    files_to_process = settings.uploaded_files if isinstance(settings.uploaded_files, list) else [settings.uploaded_files]

    # Input validation: ensure all files are PDF
    for uploaded_file in files_to_process:
        if not uploaded_file.name.lower().endswith('.pdf'):
            st.error(f"❌ Invalid file type: {uploaded_file.name}. Only PDF files are supported.")
            SessionManager.clear_results()
            return

    current_file_hash = cache_mgr.compute_file_hash(files_to_process)

    # Include ALL parameters that affect output - cache invalidates when any change
    current_settings_hash = cache_mgr.compute_settings_hash({
        'model_name': settings.model_name,
        'similarity_threshold': settings.similarity_threshold,
        'use_hybrid': settings.use_hybrid,
        'ensemble_mode': settings.ensemble_mode,
        'sdg_bert_weight': settings.sdg_bert_weight,
        'st_weight': settings.st_weight,
        'min_words': settings.min_words,
        'max_words': settings.max_words,
        'top_activities': settings.top_activities,
        'enable_sdg17_correction': settings.enable_sdg17_correction,
        'enable_sdg11_correction': settings.enable_sdg11_correction,
        'use_custom_thresholds': settings.use_custom_thresholds,
        'sdg_thresholds': settings.sdg_thresholds,
        # Hash model config to detect code/config changes
        'model_config': str(settings.model_name) + str(settings.use_hybrid),
    })

    # Check if we need to reprocess
    should_reprocess, reason = cache_mgr.should_reprocess(current_file_hash, current_settings_hash)

    # Processing status container
    status_container = st.empty()

    if should_reprocess:
        if reason == "new_files":
            status_container.info("Processing new files...")
        elif reason == "settings_changed":
            status_container.info("Re-analyzing with new settings (extraction cached)...")
        else:
            status_container.info("Processing files...")

    # Process files
    all_results = []
    sdg_mention_results = {}
    for uploaded_file in files_to_process:
        file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()

        # Check if we have this file cached
        cached_result = cache_mgr.get_cached_result(file_hash)
        if cached_result and not should_reprocess:
            all_results.append(cached_result)
            continue

        # Process new file
        progress_container = st.empty()
        progress_bar = progress_container.progress(0, f"Starting analysis of {uploaded_file.name}...")

        try:
            results = process_pdf(
                uploaded_file,
                model_name=settings.model_name,
                similarity_threshold=settings.similarity_threshold,
                use_hybrid=settings.use_hybrid,
                ensemble_mode=settings.ensemble_mode,
                sdg_bert_weight=settings.sdg_bert_weight,
                st_weight=settings.st_weight,
                min_words=settings.min_words,
                max_words=settings.max_words,
                top_activities=settings.top_activities if settings.top_activities > 0 else None,
                enable_sdg17_correction=settings.enable_sdg17_correction,
                enable_sdg11_correction=settings.enable_sdg11_correction,
                use_custom_thresholds=settings.use_custom_thresholds,
                sdg_thresholds=settings.sdg_thresholds,
                progress_bar=progress_bar
            )

            progress_container.empty()

            if "error" in results:
                st.error(f"❌ Error processing {uploaded_file.name}: {results['error']}")
                if 'traceback' in results:
                    with st.expander("Show error details"):
                        st.code(results['traceback'])
                continue

            # Cache the result
            cache_mgr.cache_result(file_hash, results)
            all_results.append(results)

            # Also scan for SDG mentions (cached)
            try:
                # Reset file read position for scanning
                uploaded_file.seek(0)
                file_bytes = uploaded_file.read()

                # Scan for SDG mentions (cached)
                sdg_mention_result = scan_sdg_mentions_cached(file_bytes, uploaded_file.name)
                if "error" not in sdg_mention_result:
                    sdg_mention_results[uploaded_file.name] = sdg_mention_result
                else:
                    st.warning(f"⚠️ SDG mention scan failed for {uploaded_file.name}: {sdg_mention_result['error']}")

                # Reset file read position for subsequent operations
                uploaded_file.seek(0)
            except Exception as e:
                logger.warning(f"SDG mention scan failed for {uploaded_file.name}: {e}")
                st.warning(f"⚠️ SDG mention scan failed for {uploaded_file.name}: {e}")

        except Exception as e:
            progress_container.empty()
            st.error(f"❌ Error processing {uploaded_file.name}: {e}")
            import traceback
            with st.expander("Show error details"):
                st.code(traceback.format_exc())
            continue

    # Clear processing status messages
    status_container.empty()

    if not all_results:
        st.error("No files were successfully processed")
        return

    # Store file names in session state for sidebar to use
    file_names = []
    for r in all_results:
        source = r.get('source', 'Unknown')
        file_names.append(source.split('/')[-1] if '/' in source else source)
    st.session_state.processed_file_names = file_names

    # Store SDG mention results in session state
    SessionManager.set(CacheKey.SDG_MENTION_RESULTS, sdg_mention_results)

    # Show results with file selector in main area
    if len(file_names) > 1:
        st.markdown("### 📁 Select Report")

        view_option = st.radio(
            "Choose view:",
            ["Single Report", "All Reports"],
            horizontal=True,
            key="view_option"
        )

        if view_option == "Single Report":
            selected_idx = st.radio(
                "Choose a report to view:",
                range(len(file_names)),
                format_func=lambda i: file_names[i],
                horizontal=True,
                key="main_report_selector"
            )
            results = all_results[selected_idx]
            show_all_reports = False
        else:
            results = None
            show_all_reports = True
    else:
        results = all_results[0]
        show_all_reports = False

    # Show mode info in main area
    if settings.use_hybrid:
        st.success(f"✓ Using Hybrid Ensemble (sdgBERT: {settings.sdg_bert_weight:.0%}, ST: {settings.st_weight:.0%})")
    else:
        st.info("Using Sentence Transformer only")

    # Show bias correction status
    bias_info = []
    if settings.enable_sdg17_correction:
        bias_info.append("SDG 17")
    if settings.enable_sdg11_correction:
        bias_info.append("SDG 11")

    if bias_info:
        st.caption(f"🔧 Bias corrections enabled: {', '.join(bias_info)}")

    # Get SDG mention results from session state
    sdg_mentions = SessionManager.get(CacheKey.SDG_MENTION_RESULTS)

    # Show results tabs
    if len(all_results) > 1:
        tabs = st.tabs(TABS_MULTI)

        with tabs[0]:  # Overview
            if show_all_reports:
                render_radar_chart(results, all_results=all_results)
            else:
                render_overview(results)
                render_radar_chart(results)

        with tabs[1]:  # Top SDGs
            if show_all_reports:
                st.info("Select a single report to view Top SDGs details")
            else:
                render_top_sdgs(results)
                render_gaps(results)

        with tabs[2]:  # Heatmap
            if show_all_reports:
                st.info("Select a single report to view Heatmap")
            else:
                render_heatmap(results)

        with tabs[3]:  # Activities
            if show_all_reports:
                st.info("Select a single report to view Activities")
            else:
                render_activities_table(results)

        with tabs[4]:  # Side-by-Side
            render_side_by_side_comparison(all_results)

        with tabs[5]:  # Comparison
            render_multi_report_comparison(all_results, settings.similarity_threshold)

        with tabs[6]:  # Keywords
            render_sdg_keyword_analysis(all_results)

        with tabs[7]:  # SDG Mentions
            render_sdg_mentions_tab(all_results, sdg_mentions)

        with tabs[8]:  # Download
            if show_all_reports:
                for idx, r in enumerate(all_results):
                    source = r.get('source', 'Unknown')
                    file_name = source.split('/')[-1] if '/' in source else source
                    st.subheader(f"📄 {file_name}")
                    render_download_buttons(r, key_suffix=f"_{idx}")
            else:
                render_download_buttons(results)
    else:
        tabs = st.tabs(TABS_SINGLE)

        with tabs[0]:  # Overview
            render_overview(results)
            render_radar_chart(results)

        with tabs[1]:  # Top SDGs
            render_top_sdgs(results)
            render_gaps(results)

        with tabs[2]:  # Heatmap
            render_heatmap(results)

        with tabs[3]:  # Activities
            render_activities_table(results)

        with tabs[4]:  # SDG Mentions
            render_single_report_sdg_mentions(results, sdg_mentions)

        with tabs[5]:  # Download
            render_download_buttons(results)


if __name__ == "__main__":
    main()