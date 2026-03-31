"""Landing page component for the dashboard."""

import streamlit as st

from src.dashboard.utils import SDG_COLORS, SDG_DATA
from src.dashboard.styles import get_landing_page_styles


def render_landing_page():
    """Render the professional landing page with all sections."""
    # Apply CSS styles
    st.markdown(get_landing_page_styles(), unsafe_allow_html=True)

    # Hero Section
    st.markdown("""
    <div class="hero-container">
        <div class="hero-content">
            <div class="hero-badge" style="font-size: 1.3rem; padding: 0.75rem 0.5rem;">
                🏙️ Local Government &nbsp;&nbsp;|&nbsp;&nbsp; 🤖 AI-Powered &nbsp;&nbsp;|&nbsp;&nbsp; 📊 Real-time Analysis
            </div>
            <h1 class="hero-title" style="font-size: 2.2rem; margin-top: 0rem; opacity: 0.95;">
                Sustainable Development Goals Alignment
            </h1>
            <p class="hero-subtitle">
                Analyze how council annual reports align with the UN's 17 Sustainable Development Goals
                using advanced AI. Transform city activities into actionable sustainability insights.
            </p>
            <div class="hero-stats">
                <div class="hero-stat">
                    <span class="hero-stat-number">17</span>
                    <span class="hero-stat-label">SDGs</span>
                </div>
                <div class="hero-stat">
                    <span class="hero-stat-number">90%+</span>
                    <span class="hero-stat-label">Accuracy</span>
                </div>
                <div class="hero-stat">
                    <span class="hero-stat-number">Hybrid</span>
                    <span class="hero-stat-label">AI Engine</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Features Section
    st.markdown("""
    <div class="features-section">
        <div class="section-header">
            <h2 class="section-title">Powerful Features</h2>
            <p class="section-subtitle">
                Everything you need to analyze sustainability alignment across your organization
            </p>
        </div>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-title">Hybrid AI Engine</div>
                <div class="feature-description">
                    Combines state-of-the-art sentence transformers with sdgBERT for 90-92% accuracy.
                    Ensemble learning delivers superior results over single-model approaches.
                </div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📄</div>
                <div class="feature-title">Smart PDF Processing</div>
                <div class="feature-description">
                    Automatically extracts meaningful activities from annual reports with
                    intelligent section detection and content filtering.
                </div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Interactive Visualizations</div>
                <div class="feature-description">
                    Beautiful charts, heatmaps, radar plots, and comparative analyses.
                    Export your results in multiple formats for reports and presentations.
                </div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <div class="feature-title">Gap Analysis</div>
                <div class="feature-description">
                    Identify SDGs with low alignment coverage and discover opportunities
                    for improvement in your sustainability strategy.
                </div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔄</div>
                <div class="feature-title">Side-by-Side Comparison</div>
                <div class="feature-description">
                    Compare two annual reports directly. See how SDG alignment differs
                    between councils or track changes year-over-year.
                </div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🎯</div>
                <div class="feature-title">Keyword Insights</div>
                <div class="feature-description">
                    Extract and visualize top keywords for each SDG. Understand language
                    patterns and themes in your sustainability reporting.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # SDGs Section
    st.markdown("""
    <div class="sdg-section">
        <div class="section-header">
            <h2 class="section-title">The 17 Sustainable Development Goals</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # SDG Interactive Grid
    cols = st.columns(3)
    for i in range(1, 18):
        col_idx = (i - 1) % 3
        with cols[col_idx]:
            sdg = SDG_DATA[i]
            color = SDG_COLORS[i]

            st.markdown(f"""
            <div class="sdg-card" style="border-left: 4px solid {color};">
                <div class="sdg-number" style="color: {color};">{i:02d}</div>
                <div class="sdg-content">
                    <div class="sdg-name" style="color: {color};">
                        {sdg['icon']} {sdg['name']}
                    </div>
                    <div class="sdg-description">{sdg['description']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # How It Works Section
    st.markdown("""
    <div class="how-it-works">
        <div class="section-header">
            <h2 class="section-title">How It Works</h2>
            <p class="section-subtitle">
                Get started in minutes with our streamlined analysis workflow
            </p>
        </div>
        <div class="steps-container">
            <div class="step-card">
                <div class="step-number">1</div>
                <div class="step-title">Upload Reports</div>
                <div class="step-description">
                    Drag and drop your council annual reports (PDF). Support for multiple files.
                </div>
            </div>
            <div class="step-card">
                <div class="step-number">2</div>
                <div class="step-title">AI Processing</div>
                <div class="step-description">
                    Our hybrid AI engine extracts activities and scores alignment with all 17 SDGs.
                </div>
            </div>
            <div class="step-card">
                <div class="step-number">3</div>
                <div class="step-title">Explore Insights</div>
                <div class="step-description">
                    Interactive visualizations, gap analysis, and comparison tools at your fingertips.
                </div>
            </div>
            <div class="step-card">
                <div class="step-number">4</div>
                <div class="step-title">Export & Share</div>
                <div class="step-description">
                    Download results in CSV, JSON, or visualization formats for your reports.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Start Section
    st.markdown("""
    <div class="quick-start">
        <h2 class="quick-start-title">Ready to Analyze Your Reports?</h2>
        <p class="quick-start-subtitle">
            Use the sidebar on the left to upload your PDF files and configure analysis settings.
            Start exploring your sustainability alignment today.
        </p>
        <div style="font-size: 3rem; margin: 2rem 0;">👈</div>
        <p style="opacity: 0.7;">Open the left sidebar to get started</p>
    </div>
    """, unsafe_allow_html=True)

    # Help Section
    st.markdown("""
    <div class="help-section">
        <div class="section-header">
            <h2 class="section-title">Help & FAQ</h2>
            <p class="section-subtitle">
                Common questions and answers to help you get the most out of the analyzer
            </p>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("**What file formats are supported?**"):
        st.markdown("""
        The SDG Alignment Analyzer currently supports **PDF files** as input.
        These should be text-based PDFs (not scanned images) for best results.
        Annual reports, strategic plans, and other council documents in PDF format work best.
        """)

    with st.expander("**How does the hybrid AI engine work?**"):
        st.markdown("""
        The hybrid engine combines two powerful AI models:

        1. **Sentence Transformers** - Creates semantic embeddings of text
        2. **sdgBERT** - Specialized BERT model fine-tuned for SDG classification

        By combining both models in an ensemble, we achieve 90-92% accuracy compared to
        87.6% with sentence transformers alone. You can adjust the ensemble weights in settings.
        """)

    with st.expander("**What is the similarity threshold?**"):
        st.markdown("""
        The similarity threshold determines when an activity is considered "aligned" with an SDG.
        - **0.5 (Standard)**: Good for general analysis with slightly higher false positive rate
        - **0.7 (High)**: Recommended for much lower false positive rate

        Higher thresholds = fewer but stronger alignments. Lower thresholds = more alignments.
        """)

    with st.expander("**Can I analyze multiple reports at once?**"):
        st.markdown("""
        Yes! Upload multiple PDFs to:
        - Compare SDG alignment across different councils
        - Track trends over multiple years
        - Generate aggregate statistics and visualizations

        When multiple files are uploaded, a "Comparison" tab will appear with multi-report analysis.
        """)

    with st.expander("**What are SDG Gaps?**"):
        st.markdown("""
        SDG Gaps are areas where your reports show little to no alignment with specific SDGs.
        This helps identify:
        - Underreported sustainability areas
        - Opportunities for improvement
        - Strategic gaps in your organization's sustainability approach
        """)

    with st.expander("**How accurate is the analysis?**"):
        st.markdown("""
        Accuracy depends on the model configuration:

        | Mode | Accuracy | Notes |
        |------|----------|-------|
        | Sentence Transformer | ~87.6% | Fast, good for quick analysis |
        | sdgBERT | ~90% | Specialized for SDG classification |
        | Hybrid Ensemble | 90-92% | Recommended for best results |

        Results are most accurate when annual reports contain clear, detailed descriptions
        of activities and outcomes.
        """)

    st.markdown("""
    </div>
    """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer">
        <div class="footer-text">
            <p>SDG Alignment Analyzer | Powered by Advanced NLP & Machine Learning</p>
            <p>Aligning with the UN Sustainable Development Goals</p>
            <p>Copyrights 2026: Alfons Palangkaraya, Dina Lahanis, Christine Jubb </p>  
        </div>
    </div>
    """, unsafe_allow_html=True)