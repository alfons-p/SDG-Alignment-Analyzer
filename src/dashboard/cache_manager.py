"""Cache management for file processing and settings.

Provides centralized logic for computing hashes and determining when
files need to be reprocessed based on file changes or settings changes.
"""

import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from src.dashboard.session import SessionManager, CacheKey


class CacheManager:
    """Manages file and settings caching logic.

    Usage:
        cache_mgr = CacheManager()

        # Compute hashes
        file_hash = cache_mgr.compute_file_hash(uploaded_files)
        settings_hash = cache_mgr.compute_settings_hash(settings_dict)

        # Check if reprocessing needed
        if cache_mgr.should_reprocess(file_hash, settings_hash):
            results = process_files(...)
            cache_mgr.cache_result(file_hash, results)
    """

    def __init__(self, session_manager: Optional[SessionManager] = None):
        """Initialize cache manager.

        Args:
            session_manager: Optional SessionManager instance. If not provided,
                           uses the default SessionManager class.
        """
        self.session = session_manager or SessionManager

    def compute_file_hash(self, files: List[Any]) -> str:
        """Compute combined hash for all uploaded files.

        Args:
            files: List of uploaded file objects (Streamlit UploadedFile)

        Returns:
            MD5 hash string representing all files
        """
        if not files:
            return ""

        hashes = []
        for f in files:
            try:
                content = f.getvalue() if hasattr(f, 'getvalue') else str(f).encode()
                file_hash = hashlib.md5(content).hexdigest()
                hashes.append(file_hash)
            except (IOError, OSError) as e:
                # If we can't read the file, raise - don't silently use name as fallback
                raise ValueError(f"Cannot read file {getattr(f, 'name', str(f))}: {e}")

        # Combine individual file hashes into one master hash
        combined = ''.join(sorted(hashes))  # Sort for consistency
        return hashlib.md5(combined.encode()).hexdigest()

    def compute_settings_hash(self, settings: Dict[str, Any]) -> str:
        """Compute hash for settings dictionary.

        Args:
            settings: Dictionary of settings (model, threshold, etc.)

        Returns:
            MD5 hash string representing the settings
        """
        # Convert to string with sorted keys for consistency
        settings_str = str(sorted(settings.items()))
        return hashlib.md5(settings_str.encode()).hexdigest()

    def get_cached_result(self, file_hash: str) -> Optional[Any]:
        """Get cached result for a specific file hash.

        Args:
            file_hash: The hash of the file to look up

        Returns:
            The cached result if found, None otherwise
        """
        results = self.session.get(CacheKey.PROCESSED_RESULTS)
        if results and isinstance(results, dict):
            return results.get(file_hash)
        return None

    def cache_result(self, file_hash: str, result: Any) -> None:
        """Cache a result for a specific file hash.

        Args:
            file_hash: The hash of the file
            result: The result data to cache
        """
        results = self.session.get(CacheKey.PROCESSED_RESULTS) or {}
        if not isinstance(results, dict):
            results = {}
        results[file_hash] = result
        self.session.set(CacheKey.PROCESSED_RESULTS, results)

    def cache_multiple_results(self, file_results: Dict[str, Any]) -> None:
        """Cache multiple results at once.

        Args:
            file_results: Dictionary mapping file hashes to results
        """
        results = self.session.get(CacheKey.PROCESSED_RESULTS) or {}
        if not isinstance(results, dict):
            results = {}
        results.update(file_results)
        self.session.set(CacheKey.PROCESSED_RESULTS, results)

    def get_all_cached_hashes(self) -> List[str]:
        """Get list of all cached file hashes.

        Returns:
            List of file hash strings
        """
        results = self.session.get(CacheKey.PROCESSED_RESULTS)
        if results and isinstance(results, dict):
            return list(results.keys())
        return []

    def should_reprocess(
        self,
        current_file_hash: str,
        current_settings_hash: str,
        clear_on_settings_change: bool = True
    ) -> Tuple[bool, str]:
        """Determine if files need reprocessing.

        Args:
            current_file_hash: Hash of current files
            current_settings_hash: Hash of current settings
            clear_on_settings_change: Whether to clear results when settings change

        Returns:
            Tuple of (should_reprocess, reason)
            - should_reprocess: True if files need reprocessing
            - reason: String explaining why ("new_files", "settings_changed", "cache_miss", "no_change")
        """
        last_file_hash = self.session.get(CacheKey.CURRENT_FILE_HASHES)
        last_settings_hash = self.session.get(CacheKey.LAST_SETTINGS_HASH)

        # Handle case where last_file_hash is a list (legacy) or string
        if isinstance(last_file_hash, list):
            last_file_hash = ''.join(sorted(last_file_hash))

        # Check if files changed
        files_changed = current_file_hash != last_file_hash

        if files_changed:
            # Files changed - clear everything
            self.session.clear_results()
            self.session.set(CacheKey.CURRENT_FILE_HASHES, current_file_hash)
            self.session.set(CacheKey.LAST_SETTINGS_HASH, current_settings_hash)
            return True, "new_files"

        # Check if settings changed
        settings_changed = current_settings_hash != last_settings_hash

        if settings_changed:
            if clear_on_settings_change:
                # Clear results to trigger reprocessing with new settings
                self.session.set(CacheKey.PROCESSED_RESULTS, {})
            self.session.set(CacheKey.LAST_SETTINGS_HASH, current_settings_hash)
            return True, "settings_changed"

        # Check if we have all results cached
        cached_results = self.session.get(CacheKey.PROCESSED_RESULTS)
        if not cached_results or current_file_hash not in cached_results:
            return True, "cache_miss"

        return False, "no_change"

    def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status.

        Returns:
            Dictionary with processing status information
        """
        return self.session.get_state_summary()

    def invalidate_cache(self) -> None:
        """Manually invalidate all cached results."""
        self.session.clear_results()
        self.session.set(CacheKey.LAST_SETTINGS_HASH, None)

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        results = self.session.get(CacheKey.PROCESSED_RESULTS)
        file_hash = self.session.get(CacheKey.CURRENT_FILE_HASHES)
        # file_hash can be a string or list
        hash_count = 1 if isinstance(file_hash, str) and file_hash else len(file_hash) if file_hash else 0
        return {
            "cached_files": len(results) if isinstance(results, dict) else 0,
            "current_file_hashes": hash_count,
        }
