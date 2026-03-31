"""Path constants and utilities for SDG Alignment Analyzer."""

from pathlib import Path
from typing import Dict, List

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"

# Cache directories
CACHE_DIR = PROJECT_ROOT / ".cache"

# Model directories
MODELS_DIR = PROJECT_ROOT / "models"

# Test directories
TESTS_DIR = PROJECT_ROOT / "tests"

# Default directory structure
DEFAULT_DIRS: List[Path] = [
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    RESULTS_DIR,
    CACHE_DIR,
]

# Results subdirectories
RESULTS_SUBDIRS = {
    'by_council': RESULTS_DIR / "by_council",
    'trends': RESULTS_DIR / "trends",
    'state_analysis': RESULTS_DIR / "state_analysis",
    'sdg_keywords': RESULTS_DIR / "sdg_keywords",
}

# Ensure all default directories exist
for dir_path in DEFAULT_DIRS + list(RESULTS_SUBDIRS.values()):
    dir_path.mkdir(parents=True, exist_ok=True)