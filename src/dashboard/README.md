# Dashboard Module

Modular Streamlit dashboard for the SDG Alignment Analyzer. This module provides UI components, caching, processing pipelines, and visualization functions.

## Architecture

```
src/dashboard/
├── __init__.py              # Re-exports all public components
├── styles.py                # CSS styles for landing page
├── caching.py               # @st.cache_resource decorators
├── utils.py                 # Helper functions and constants
├── session.py               # Session state management
├── cache_manager.py         # File-based cache management
├── components/
│   ├── __init__.py           # Re-exports all render functions
│   ├── header.py             # render_header()
│   ├── landing.py            # render_landing_page()
│   ├── sidebar.py            # render_sidebar_settings()
│   ├── overview.py           # render_overview(), render_gaps()
│   ├── visualizations.py     # render_top_sdgs(), render_radar_chart(), render_heatmap()
│   ├── tables.py             # render_activities_table()
│   ├── comparison.py         # render_side_by_side_comparison(), render_multi_report_comparison()
│   ├── keywords.py           # render_sdg_keyword_analysis()
│   ├── downloads.py          # render_download_buttons()
│   └── trends.py             # render_trend_analysis()
└── processing/
    ├── __init__.py           # Re-exports processing functions
    ├── extraction.py         # extract_activities_from_pdf_cached()
    └── alignment.py          # align_activities_with_sdgs(), process_pdf()
```

## Module Responsibilities

### Core Modules

| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `styles.py` | CSS styles for the landing page | `STYLES`, `get_landing_page_styles()` |
| `caching.py` | Streamlit resource caching | `get_cached_sdg_ref()`, `get_cached_engine()`, `get_cached_hybrid_engine()` |
| `utils.py` | Constants and helper functions | `SDG_COLORS`, `SDG_DATA`, `get_chart_theme_colors()`, `get_score_color()` |
| `session.py` | Session state management | `SessionManager`, `CacheKey`, `AppState` |
| `cache_manager.py` | File-based caching | `CacheManager` |

### Processing Module

The `processing/` module handles the PDF-to-alignment pipeline:

| File | Purpose |
|------|---------|
| `extraction.py` | Extracts activities from PDFs with Streamlit caching |
| `alignment.py` | Aligns activities with SDGs using ML models |

```python
from src.dashboard.processing import process_pdf

results = process_pdf(
    uploaded_file,
    model_name="all-mpnet-base-v2",
    similarity_threshold=0.3,
    use_hybrid=False
)
```

### Components Module

The `components/` module contains all render functions for UI elements:

| File | Functions | Description |
|------|-----------|-------------|
| `header.py` | `render_header()` | Simple app header when files uploaded |
| `landing.py` | `render_landing_page()` | Full landing page with hero, features, SDG grid |
| `sidebar.py` | `render_sidebar_settings()` | File upload and settings controls |
| `overview.py` | `render_overview()`, `render_gaps()` | Metrics overview and SDG gaps display |
| `visualizations.py` | `render_top_sdgs()`, `render_radar_chart()`, `render_heatmap()` | Charts and visualizations |
| `tables.py` | `render_activities_table()` | Filterable activities data table |
| `comparison.py` | `render_side_by_side_comparison()`, `render_multi_report_comparison()` | Multi-report comparison views |
| `keywords.py` | `render_sdg_keyword_analysis()` | Keyword extraction and analysis |
| `downloads.py` | `render_download_buttons()` | CSV, JSON, summary download options |
| `trends.py` | `render_trend_analysis()` | Trend analysis over time |

## Usage

### Basic Import

```python
from src.dashboard import (
    # Components
    render_landing_page,
    render_header,
    render_sidebar_settings,
    render_overview,
    render_gaps,
    render_top_sdgs,
    # Processing
    process_pdf,
    # Caching
    get_cached_engine,
)
```

### Processing a PDF

```python
from src.dashboard.processing import process_pdf

# Process with default settings
results = process_pdf(uploaded_file)

# Process with hybrid ensemble
results = process_pdf(
    uploaded_file,
    model_name="all-mpnet-base-v2",
    similarity_threshold=0.7,
    use_hybrid=True,
    sdg_bert_weight=0.55,
    st_weight=0.45
)
```

### Rendering Components

```python
import streamlit as st
from src.dashboard.components import (
    render_header,
    render_sidebar_settings,
    render_overview,
)

def main():
    render_header()
    files, settings = render_sidebar_settings()

    if files:
        render_overview(results)

if __name__ == "__main__":
    main()
```

## Design Principles

1. **Single Responsibility**: Each module handles one concern
2. **Thin Orchestrator**: `app.py` only imports and coordinates, no business logic
3. **Theme-Aware**: All visualizations use `get_chart_theme_colors()` for light/dark mode
4. **Cached Resources**: Model loading uses `@st.cache_resource` to avoid reloads
5. **Cached Data**: PDF extraction uses `@st.cache_data` to avoid reprocessing

## File Size Guidelines

Following CLAUDE.md guidelines, all modules are under 500 lines:

| File | Lines |
|------|-------|
| `styles.py` | ~412 |
| `components/comparison.py` | ~415 |
| `components/trends.py` | ~425 |
| `components/landing.py` | ~278 |
| Other files | < 200 |

## Testing

Import tests verify module structure:

```python
# Test imports work
from src.dashboard import render_landing_page, process_pdf, get_cached_engine
from src.dashboard.components import render_header, render_sidebar_settings
from src.dashboard.processing import extract_activities_from_pdf_cached
```