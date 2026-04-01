"""Session state management for Streamlit dashboard.

Provides centralized, type-safe session state management with enum-based keys
to avoid magic strings and scattered initialization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import streamlit as st


class CacheKey(Enum):
    """Session state keys to avoid magic strings throughout the codebase."""
    PROCESSED_RESULTS = "processed_results"
    CURRENT_FILE_HASHES = "current_file_hashes"
    LAST_SETTINGS_HASH = "last_settings_hash"
    UPLOADED_FILES = "uploaded_files"
    CURRENT_VIEW = "current_view"
    PROCESSING_STATE = "processing_state"
    SELECTED_REPORT_INDEX = "selected_report_index"
    SDG_MENTION_RESULTS = "sdg_mention_results"


@dataclass
class ProcessingState:
    """State for background processing."""
    is_processing: bool = False
    progress: float = 0.0
    current_file: str = ""
    errors: List[str] = field(default_factory=list)


@dataclass
class AppState:
    """Type-safe application state container."""
    processed_results: Dict[str, Any] = field(default_factory=dict)
    current_file_hashes: List[str] = field(default_factory=list)
    last_settings_hash: Optional[str] = None
    uploaded_files: List[Any] = field(default_factory=list)
    current_view: str = "landing"
    processing_state: ProcessingState = field(default_factory=ProcessingState)
    selected_report_index: int = 0


class SessionManager:
    """Centralized session state management for Streamlit.

    Usage:
        SessionManager.init()  # Call once at app start

        # Get values
        results = SessionManager.get(CacheKey.PROCESSED_RESULTS)

        # Set values
        SessionManager.set(CacheKey.CURRENT_VIEW, "analysis")

        # Clear results
        SessionManager.clear_results()
    """

    _DEFAULTS: Dict[CacheKey, Any] = {
        CacheKey.PROCESSED_RESULTS: {},
        CacheKey.CURRENT_FILE_HASHES: [],
        CacheKey.LAST_SETTINGS_HASH: None,
        CacheKey.UPLOADED_FILES: [],
        CacheKey.CURRENT_VIEW: "landing",
        CacheKey.PROCESSING_STATE: ProcessingState(),
        CacheKey.SELECTED_REPORT_INDEX: 0,
        CacheKey.SDG_MENTION_RESULTS: {},
    }

    @classmethod
    def init(cls) -> None:
        """Initialize all session state keys with defaults.

        Safe to call multiple times - only sets values if keys don't exist.
        """
        for key, default in cls._DEFAULTS.items():
            if key.value not in st.session_state:
                st.session_state[key.value] = default

    @classmethod
    def get(cls, key: CacheKey) -> Any:
        """Type-safe getter for session state values.

        Args:
            key: The CacheKey to retrieve

        Returns:
            The stored value, or the default if not set
        """
        return st.session_state.get(key.value, cls._DEFAULTS[key])

    @classmethod
    def set(cls, key: CacheKey, value: Any) -> None:
        """Type-safe setter for session state values.

        Args:
            key: The CacheKey to set
            value: The value to store
        """
        st.session_state[key.value] = value

    @classmethod
    def clear_results(cls) -> None:
        """Clear only results-related state.

        Use this when files change or when you want to force reprocessing.
        """
        st.session_state[CacheKey.PROCESSED_RESULTS.value] = {}
        st.session_state[CacheKey.CURRENT_FILE_HASHES.value] = []

    @classmethod
    def clear_all(cls) -> None:
        """Clear all application state.

        Use this for a complete reset (e.g., user logout, major mode change).
        """
        for key, default in cls._DEFAULTS.items():
            st.session_state[key.value] = default

    @classmethod
    def has_key(cls, key: CacheKey) -> bool:
        """Check if a key exists in session state.

        Args:
            key: The CacheKey to check

        Returns:
            True if the key exists
        """
        return key.value in st.session_state

    @classmethod
    def get_state_summary(cls) -> Dict[str, Any]:
        """Get a summary of current session state for debugging.

        Returns:
            Dictionary with state information
        """
        return {
            "processed_count": len(cls.get(CacheKey.PROCESSED_RESULTS)),
            "file_hashes_count": len(cls.get(CacheKey.CURRENT_FILE_HASHES)),
            "current_view": cls.get(CacheKey.CURRENT_VIEW),
            "has_settings_hash": cls.get(CacheKey.LAST_SETTINGS_HASH) is not None,
            "processing": cls.get(CacheKey.PROCESSING_STATE).is_processing,
        }


def get_session() -> SessionManager:
    """Get the SessionManager class (for use in function signatures).

    Returns:
        The SessionManager class
    """
    return SessionManager
