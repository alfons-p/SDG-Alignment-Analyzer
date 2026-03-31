"""Header component for the dashboard."""

import streamlit as st


def render_header():
    """Render the simple app header (when files are uploaded)."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #000000 0%, #1a1a1a 50%, #333333 100%);
                padding: 2rem 0.5rem; border-radius: 0rem; margin-bottom: 0rem; color: white;
                box-shadow: 0 10px 10px rgba(0, 0, 0, 0.3);">
        <div style="display: flex; align-items: center; gap: 0rem; flex-wrap: wrap;">
            <!-- Professional Logo with City Icon -->
            <div style="display: flex; align-items: center; gap: 0.25rem;">
                <div style="
                    width: 30px;
                    height: 30px;
                    background: linear-gradient(135deg, #E03C31 0%, #f44a44 100%);
                    border-radius: 2px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.2rem;
                    box-shadow: 0 2px 8px rgba(224, 60, 49, 0.4);
                ">🏙️</div>
                <div style="border-left: 2px solid rgba(255,255,255,0.3); height: 30px;"></div>
                <div>
                    <h1 style="margin: 0; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.5px; color: #ffffff;">
                        SDG Alignment Analyzer
                    </h1>
                </div>
            </div>
            <div style="margin-left: auto; display: flex; gap: 0.5rem; align-items: center;">
                <span style="background: rgba(224, 60, 49, 0.2); color: #f44a44; padding: 0.25rem 0.5rem;
                             border-radius: 50px; font-size: 0.7rem; font-weight: 600; border: 1px solid rgba(224, 60, 49, 0.4);">
                    🤖 AI-Powered
                </span>
                <span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 0.25rem 0.5rem;
                             border-radius: 50px; font-size: 0.7rem; font-weight: 600; border: 1px solid rgba(59, 130, 246, 0.4);">
                    📊 Real-time
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)