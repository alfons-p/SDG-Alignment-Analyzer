"""CSS styles for the SDG Alignment Analyzer dashboard."""

STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Main container */
    .main > div {
        padding: 0 !important;
    }

    /* Swinburne-inspired Professional Theme */
    :root {
        --primary: #E03C31;
        --primary-light: #f44a44;
        --primary-lighter: #f77066;
        --accent: #E03C31;
        --accent-light: #f44a44;
        --success: #10b981;
        --warning: #f59e0b;
        --text: #1e293b;
        --text-light: #64748b;
        --border: #e2e8f0;
        --background: #ffffff;
        --background-alt: #f8fafc;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 0.95rem;
        border-radius: 8px 8px 0 0;
        background: transparent;
        border: none;
        color: var(--text-light);
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(224, 60, 49, 0.1);
        color: var(--primary);
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary), var(--primary-light));
        color: white;
        box-shadow: 0 4px 15px rgba(224, 60, 49, 0.3);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 500;
    }

    /* Section headers */
    h3 {
        font-weight: 700 !important;
        color: var(--primary) !important;
        margin-bottom: 1rem !important;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: white;
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid var(--border);
    }

    .streamlit-expanderHeader:hover {
        background: var(--background-alt);
    }

    /* Metric styling */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid var(--border);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        color: var(--text-light);
        font-weight: 500;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary);
    }

    /* Alert styling */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: 8px;
    }

    /* DataFrame/Table styling */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }

    /* Ensure content doesn't get cut off by sidebar */
    .main .block-container {
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }

    section[data-testid="stSidebar"] {
        z-index: 100;
    }

    .main {
        overflow-x: hidden;
    }

    /* Hero Section - Swinburne Red */
    .hero-container {
        background: linear-gradient(135deg, #E03C31 0%, #f44a44 50%, #f77066 100%);
        padding: 4rem 2rem;
        border-radius: 0 0 2rem 2rem;
        margin: -2rem 0 2rem 0;
        box-shadow: 0 20px 60px rgba(224, 60, 49, 0.3);
    }

    .hero-content {
        max-width: 1200px;
        margin: 0 auto;
        text-align: center;
        color: white;
    }

    .hero-badge {
        display: inline-block;
        background: rgba(255,255,255,0.25);
        backdrop-filter: blur(10px);
        padding: 0.5rem 1.5rem;
        border-radius: 50px;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,0.4);
    }

    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 1rem;
        line-height: 1.1;
        text-shadow: 0 2px 20px rgba(0,0,0,0.15);
    }

    .hero-subtitle {
        font-size: 1.3rem;
        font-weight: 400;
        opacity: 0.95;
        max-width: 700px;
        margin: 0 auto 2rem auto;
        line-height: 1.6;
    }

    .hero-stats {
        display: flex;
        justify-content: center;
        gap: 3rem;
        margin-top: 2rem;
        flex-wrap: wrap;
    }

    .hero-stat {
        text-align: center;
    }

    .hero-stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        display: block;
    }

    .hero-stat-label {
        font-size: 0.9rem;
        opacity: 0.85;
    }

    /* Feature Cards */
    .features-section {
        padding: 3rem 2rem;
        max-width: 1400px;
        margin: 0 auto;
    }

    .section-header {
        text-align: center;
        margin-bottom: 3rem;
    }

    .section-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 0.5rem;
    }

    .section-subtitle {
        font-size: 1.1rem;
        color: var(--text-light);
        max-width: 600px;
        margin: 0 auto;
    }

    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin-top: 2rem;
    }

    .feature-card {
        background: white;
        border-radius: 1rem;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        border: 1px solid var(--border);
        transition: all 0.3s ease;
    }

    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        border-color: var(--primary);
    }

    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }

    .feature-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--primary);
        margin-bottom: 0.5rem;
    }

    .feature-description {
        font-size: 0.95rem;
        color: var(--text-light);
        line-height: 1.6;
    }

    /* SDG Grid */
    .sdg-section {
        background: var(--background-alt);
        padding: 4rem 2rem;
        margin: 2rem 0;
    }

    .sdg-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1rem;
        max-width: 1400px;
        margin: 0 auto;
    }

    .sdg-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        border-radius: 0.75rem;
        background: white;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        cursor: pointer;
        border: 2px solid transparent;
    }

    .sdg-card:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }

    .sdg-number {
        font-size: 1.5rem;
        font-weight: 800;
        opacity: 0.3;
        min-width: 40px;
    }

    .sdg-content {
        flex: 1;
    }

    .sdg-name {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.2rem;
    }

    .sdg-description {
        font-size: 0.8rem;
        opacity: 0.7;
        line-height: 1.3;
    }

    /* How It Works */
    .how-it-works {
        padding: 4rem 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    .steps-container {
        display: flex;
        justify-content: space-between;
        gap: 2rem;
        margin-top: 3rem;
        flex-wrap: wrap;
    }

    .step-card {
        flex: 1;
        min-width: 200px;
        text-align: center;
        position: relative;
    }

    .step-number {
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, var(--primary), var(--primary-light));
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0 auto 1rem auto;
        box-shadow: 0 10px 30px rgba(224, 60, 49, 0.3);
    }

    .step-title {
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        color: var(--primary);
    }

    .step-description {
        font-size: 0.9rem;
        color: var(--text-light);
    }

    /* Quick Start */
    .quick-start {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        padding: 4rem 2rem;
        margin: 2rem 0;
        text-align: center;
        color: white;
    }

    .quick-start-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    .quick-start-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-bottom: 2rem;
    }

    .cta-button {
        display: inline-block;
        background: white;
        color: var(--primary);
        padding: 1rem 2.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1.1rem;
        text-decoration: none;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        border: none;
        cursor: pointer;
    }

    .cta-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.25);
    }

    /* Help Section */
    .help-section {
        padding: 4rem 2rem;
        max-width: 800px;
        margin: 0 auto;
    }

    .faq-item {
        background: white;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
        overflow: hidden;
    }

    .faq-question {
        padding: 1.25rem;
        font-weight: 600;
        color: var(--primary);
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .faq-answer {
        padding: 0 1.25rem 1.25rem 1.25rem;
        color: var(--text-light);
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* Footer */
    .footer {
        background: #1e293b;
        color: white;
        padding: 2rem;
        margin: 0 0 -2rem 0;
        text-align: center;
    }

    .footer-text {
        opacity: 0.8;
        font-size: 0.9rem;
    }

    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .animate-in {
        animation: fadeInUp 0.6s ease forwards;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .hero-title {
            font-size: 2rem;
        }

        .hero-subtitle {
            font-size: 1rem;
        }

        .steps-container {
            flex-direction: column;
        }
    }
</style>
"""


def get_landing_page_styles():
    """Return the CSS styles for the landing page."""
    return STYLES