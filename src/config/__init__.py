"""Configuration package for SDG Alignment Analyzer.

This package contains configuration-related modules:
- sdg_definitions: SDG 1-17 definitions and metadata
- settings: Application configuration and settings
- paths: Path constants and utilities
"""

from .settings import Config
from .sdg_definitions import SDG_DEFINITIONS

# Create global config instance for backward compatibility
config = Config()

# Re-export for easy imports
__all__ = [
    'Config',
    'config',
    'SDG_DEFINITIONS',
]