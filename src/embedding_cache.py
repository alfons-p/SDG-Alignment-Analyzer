"""Embedding Cache Module.

Provides efficient caching for both SDG and activity embeddings with:
- Content-addressed storage (SHA256 hashes for activities)
- Version checking for cache invalidation
- Fast numpy serialization (faster than pickle)
- Optional memory mapping for large files
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import numpy as np
import pickle


class EmbeddingCache:
    """Efficient caching system for embeddings."""

    CACHE_VERSION = "2.0"  # Increment when format changes

    def __init__(self, cache_dir: Optional[Path] = None, use_memory_map: bool = False):
        """
        Initialize embedding cache.

        Args:
            cache_dir: Directory to store cache files (default: .cache/)
            use_memory_map: Whether to use memory-mapped files for large embeddings
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / ".cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.use_memory_map = use_memory_map
        self._metadata_file = self.cache_dir / "cache_metadata.json"
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"version": self.CACHE_VERSION, "entries": {}}

    def _save_metadata(self) -> None:
        """Save cache metadata."""
        try:
            with open(self._metadata_file, 'w') as f:
                json.dump(self._metadata, f, indent=2)
        except IOError as e:
            print(f"Warning: Failed to save cache metadata: {e}")

    def _get_cache_key(self, text: str, model_name: str) -> str:
        """Generate content-addressed cache key."""
        content = f"{text}:{model_name}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]

    def _get_embedding_path(self, cache_key: str, is_sdg: bool = False) -> Path:
        """Get path to embedding file."""
        prefix = "sdg" if is_sdg else "act"
        if self.use_memory_map:
            return self.cache_dir / f"{prefix}_{cache_key}.npy"
        return self.cache_dir / f"{prefix}_{cache_key}.npz"

    def _get_model_fingerprint(self, model_name: str) -> str:
        """Generate fingerprint for model versioning."""
        # Simple fingerprint based on model name and cache version
        return hashlib.sha256(
            f"{model_name}:{self.CACHE_VERSION}".encode()
        ).hexdigest()[:16]

    def get_sdg_cache_path(self, model_name: str) -> Path:
        """Get path for SDG embeddings cache."""
        safe_model_name = model_name.replace('/', '_').replace('\\', '_')
        fingerprint = self._get_model_fingerprint(model_name)
        return self.cache_dir / f"sdg_embeddings_v2_{safe_model_name}_{fingerprint}"

    def save_sdg_embeddings(
        self,
        embeddings: Dict[int, np.ndarray],
        model_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save SDG embeddings with metadata.

        Args:
            embeddings: Dictionary mapping SDG numbers to embeddings
            model_name: Name of the model used
            metadata: Additional metadata to store

        Returns:
            Path to saved cache file
        """
        cache_path = self.get_sdg_cache_path(model_name)

        # Prepare data for saving
        sdg_numbers = sorted(embeddings.keys())
        embeddings_array = np.vstack([embeddings[num] for num in sdg_numbers])

        # Save embeddings efficiently with numpy
        np.savez_compressed(
            cache_path,
            embeddings=embeddings_array,
            sdg_numbers=np.array(sdg_numbers),
            model_name=model_name,
            cache_version=self.CACHE_VERSION,
            timestamp=time.time(),
            metadata=json.dumps(metadata or {})
        )

        # Update metadata
        self._metadata["entries"][str(cache_path.name)] = {
            "model": model_name,
            "timestamp": time.time(),
            "version": self.CACHE_VERSION,
            "sdg_count": len(embeddings)
        }
        self._save_metadata()

        return cache_path

    def load_sdg_embeddings(
        self,
        model_name: str
    ) -> Optional[Tuple[Dict[int, np.ndarray], Dict[str, Any]]]:
        """
        Load SDG embeddings from cache.

        Args:
            model_name: Name of the model

        Returns:
            Tuple of (embeddings dict, metadata) or None if cache miss
        """
        cache_path = self.get_sdg_cache_path(model_name)
        npz_path = Path(str(cache_path) + ".npz")

        if not npz_path.exists():
            return None

        try:
            # Load with numpy
            data = np.load(npz_path, allow_pickle=True)

            # Check version
            stored_version = str(data.get('cache_version', '1.0'))
            if stored_version != self.CACHE_VERSION:
                print(f"Cache version mismatch: {stored_version} != {self.CACHE_VERSION}")
                return None

            # Check model name
            stored_model = str(data.get('model_name', ''))
            if stored_model != model_name:
                print(f"Cache model mismatch: {stored_model} != {model_name}")
                return None

            # Reconstruct embeddings dict
            embeddings_array = data['embeddings']
            sdg_numbers = data['sdg_numbers']

            embeddings = {}
            for i, sdg_num in enumerate(sdg_numbers):
                embeddings[int(sdg_num)] = embeddings_array[i]

            # Parse metadata
            metadata = json.loads(str(data.get('metadata', '{}')))
            metadata['cache_timestamp'] = float(data.get('timestamp', 0))

            return embeddings, metadata

        except (IOError, KeyError, ValueError) as e:
            print(f"Failed to load SDG cache: {e}")
            return None

    def get_activity_embedding(
        self,
        text: str,
        model_name: str
    ) -> Optional[np.ndarray]:
        """
        Get cached activity embedding.

        Args:
            text: Activity text
            model_name: Name of the model used

        Returns:
            Cached embedding or None if cache miss
        """
        cache_key = self._get_cache_key(text, model_name)
        cache_path = self._get_embedding_path(cache_key, is_sdg=False)

        if not cache_path.exists():
            return None

        try:
            if self.use_memory_map:
                # Memory-mapped access for large files
                return np.load(cache_path, mmap_mode='r')
            else:
                data = np.load(cache_path, allow_pickle=True)
                return data['embedding']
        except (IOError, KeyError):
            return None

    def save_activity_embedding(
        self,
        text: str,
        model_name: str,
        embedding: np.ndarray
    ) -> Path:
        """
        Save activity embedding to cache.

        Args:
            text: Activity text
            model_name: Name of the model
            embedding: The embedding array

        Returns:
            Path to saved cache file
        """
        cache_key = self._get_cache_key(text, model_name)
        cache_path = self._get_embedding_path(cache_key, is_sdg=False)

        if self.use_memory_map:
            # Direct numpy save for memory mapping
            np.save(cache_path, embedding)
        else:
            # Compressed storage
            np.savez_compressed(
                cache_path,
                embedding=embedding,
                text_hash=cache_key,
                model=model_name,
                timestamp=time.time()
            )

        return cache_path

    def get_activity_embeddings_batch(
        self,
        texts: List[str],
        model_name: str
    ) -> Tuple[List[Optional[np.ndarray]], List[int]]:
        """
        Get cached embeddings for multiple activities.

        Args:
            texts: List of activity texts
            model_name: Name of the model

        Returns:
            Tuple of (embeddings list, indices of cache misses)
        """
        embeddings = []
        cache_misses = []

        for i, text in enumerate(texts):
            emb = self.get_activity_embedding(text, model_name)
            embeddings.append(emb)
            if emb is None:
                cache_misses.append(i)

        return embeddings, cache_misses

    def save_activity_embeddings_batch(
        self,
        texts: List[str],
        model_name: str,
        embeddings: List[np.ndarray]
    ) -> List[Path]:
        """
        Save multiple activity embeddings to cache.

        Args:
            texts: List of activity texts
            model_name: Name of the model
            embeddings: List of embedding arrays

        Returns:
            List of paths to saved cache files
        """
        paths = []
        for text, embedding in zip(texts, embeddings):
            path = self.save_activity_embedding(text, model_name, embedding)
            paths.append(path)
        return paths

    def clear_cache(self, older_than_days: Optional[int] = None) -> Dict[str, int]:
        """
        Clear cache entries.

        Args:
            older_than_days: Only clear entries older than this many days

        Returns:
            Dictionary with counts of removed items
        """
        removed = {"sdg": 0, "activity": 0, "errors": 0}
        cutoff_time = time.time() - (older_than_days * 86400) if older_than_days else 0

        # Clear SDG embeddings
        for f in self.cache_dir.glob("sdg_embeddings_v2_*.npz"):
            try:
                if older_than_days:
                    data = np.load(f)
                    timestamp = float(data.get('timestamp', 0))
                    if timestamp < cutoff_time:
                        f.unlink()
                        removed["sdg"] += 1
                else:
                    f.unlink()
                    removed["sdg"] += 1
            except Exception:
                removed["errors"] += 1

        # Clear activity embeddings
        for f in self.cache_dir.glob("act_*.npz"):
            try:
                if older_than_days:
                    data = np.load(f)
                    timestamp = float(data.get('timestamp', 0))
                    if timestamp < cutoff_time:
                        f.unlink()
                        removed["activity"] += 1
                else:
                    f.unlink()
                    removed["activity"] += 1
            except Exception:
                removed["errors"] += 1

        # Clear old pickle caches (backward compatibility)
        for f in self.cache_dir.glob("sdg_embeddings_*.pkl"):
            try:
                f.unlink()
                removed["sdg"] += 1
            except Exception:
                removed["errors"] += 1

        # Update metadata
        self._metadata = {"version": self.CACHE_VERSION, "entries": {}}
        self._save_metadata()

        return removed

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "sdg_cache_files": 0,
            "activity_cache_files": 0,
            "total_size_mb": 0,
            "oldest_entry": None,
            "newest_entry": None
        }

        all_files = []

        for f in self.cache_dir.glob("*.npz"):
            try:
                size = f.stat().st_size
                mtime = f.stat().st_mtime
                stats["total_size_mb"] += size / (1024 * 1024)
                all_files.append((f.name, mtime))

                if "sdg" in f.name:
                    stats["sdg_cache_files"] += 1
                elif "act_" in f.name:
                    stats["activity_cache_files"] += 1
            except OSError:
                pass

        if all_files:
            all_files.sort(key=lambda x: x[1])
            stats["oldest_entry"] = time.strftime('%Y-%m-%d %H:%M', time.localtime(all_files[0][1]))
            stats["newest_entry"] = time.strftime('%Y-%m-%d %H:%M', time.localtime(all_files[-1][1]))

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)

        return stats
