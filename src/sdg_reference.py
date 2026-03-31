"""SDG Reference Data Module.

Manages SDG definitions, embeddings, and reference data.
Enhanced with multi-text embedding generation for richer semantic representations.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import SDG_DEFINITIONS, Config
from src.embedding_cache import EmbeddingCache
from src.exceptions import EmbeddingError


class SDGReference:
    """Manages SDG reference data and pre-computed embeddings."""

    def __init__(self, model_name: Optional[str] = None, cache_dir: Optional[Path] = None):
        """
        Initialize SDG reference.

        Args:
            model_name: Sentence transformer model name
            cache_dir: Directory to cache embeddings
        """
        self.config = Config()
        self.model_name = model_name or self.config.default_embedding_model
        self.cache_dir = cache_dir or self.config.cache_dir
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._model: Optional[SentenceTransformer] = None
        self._embeddings: Optional[Dict[int, np.ndarray]] = None

        # Initialize the new embedding cache
        self._cache = EmbeddingCache(self.cache_dir)

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the sentence transformer model with GPU support if available."""
        if self._model is None:
            # Auto-detect device: cuda > mps (Apple Silicon) > cpu
            if os.getenv("CUDA_VISIBLE_DEVICES") != "-1":
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"
            else:
                device = "cpu"

            self._model = SentenceTransformer(self.model_name, device=device)
            print(f"Loaded sentence transformer model on {device}")
        return self._model

    def _get_cache_path(self) -> Path:
        """Get path to cache file for enhanced embeddings."""
        safe_model_name = self.model_name.replace('/', '_')
        return self.cache_dir / f"sdg_embeddings_enhanced_{safe_model_name}.pkl"

    def _get_legacy_cache_path(self) -> Path:
        """Get path to legacy cache file (for backward compatibility)."""
        safe_model_name = self.model_name.replace('/', '_')
        return self.cache_dir / f"sdg_embeddings_{safe_model_name}.pkl"

    def _generate_sdg_text_variants(self, sdg_num: int) -> Dict[str, str]:
        """
        Generate multiple text variants for SDG embedding.

        Creates rich, multi-faceted embeddings by encoding different aspects
        of each SDG separately, then combining them.

        Args:
            sdg_num: The SDG number (1-17)

        Returns:
            Dictionary of text variants with their weights
        """
        sdg = SDG_DEFINITIONS.get(sdg_num, {})

        variants = {}

        # Variant 1: Core description (full description + name)
        # Weight: 0.35 - Most important, captures the essence
        core_text = f"SDG {sdg_num}: {sdg.get('name', '')}. {sdg.get('description', '')}"
        variants['core'] = core_text

        # Variant 2: Local government context
        # Weight: 0.30 - Council-specific applications
        local_gov_keywords = sdg.get('local_gov_keywords', [])
        if local_gov_keywords:
            local_text = f"Local government and council activities for {sdg.get('name', '')}: " + ", ".join(local_gov_keywords[:30])
            variants['local_gov'] = local_text
        else:
            variants['local_gov'] = core_text

        # Variant 3: UN indicators
        # Weight: 0.15 - Official measurement criteria
        indicators = sdg.get('indicators', [])
        targets = sdg.get('targets', [])
        if indicators:
            indicator_text = f"UN Sustainable Development Goals targets and indicators for {sdg.get('name', '')}: " + ", ".join(indicators[:5])
            variants['indicators'] = indicator_text
        elif targets:
            variants['indicators'] = f"SDG {sdg_num} targets: " + ", ".join(targets)
        else:
            variants['indicators'] = core_text

        # Variant 4: Keywords focus
        # Weight: 0.20 - Key concepts for matching
        all_keywords = []
        all_keywords.extend(sdg.get('keywords', []))
        all_keywords.extend(sdg.get('local_gov_keywords', [])[:20])  # Add some local gov keywords

        if all_keywords:
            keyword_text = f"Keywords for SDG {sdg_num} {sdg.get('name', '')}: " + ", ".join(all_keywords[:40])
            variants['keywords'] = keyword_text
        else:
            variants['keywords'] = core_text

        return variants

    def _combine_embeddings(self, embeddings: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Combine multiple embeddings using weighted average.

        Args:
            embeddings: Dictionary of variant name to embedding array

        Returns:
            Combined embedding vector
        """
        weights = {
            'core': 0.35,        # Core description is most important
            'local_gov': 0.30,   # Local context is crucial for council alignment
            'indicators': 0.15,  # Official criteria provide structure
            'keywords': 0.20     # Keywords help with direct matching
        }

        # Normalize weights to sum to 1
        total_weight = sum(weights.get(k, 0.25) for k in embeddings.keys())

        # Weighted combination
        combined = np.zeros_like(list(embeddings.values())[0])
        for variant, emb in embeddings.items():
            weight = weights.get(variant, 0.25) / total_weight
            combined += weight * emb

        # Normalize the combined embedding
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm

        return combined

    def generate_embeddings(self, force_regenerate: bool = False) -> Dict[int, np.ndarray]:
        """
        Generate or load cached SDG embeddings with multi-text enhancement.

        Generates richer embeddings by encoding multiple aspects of each SDG
        separately and combining them with learned weights.

        Args:
            force_regenerate: Whether to regenerate embeddings

        Returns:
            Dictionary mapping SDG numbers to embeddings
        """
        # Try to load from new cache (v2 with numpy serialization)
        if not force_regenerate:
            cached = self._cache.load_sdg_embeddings(self.model_name)
            if cached:
                self._embeddings, metadata = cached
                print(f"Loaded SDG embeddings from cache (v2) for {self.model_name}")
                return self._embeddings

            # Try legacy pickle cache for backward compatibility
            cache_path = self._get_cache_path()
            if cache_path.exists():
                try:
                    import pickle
                    with open(cache_path, 'rb') as f:
                        self._embeddings = pickle.load(f)
                    print(f"Loaded SDG embeddings from legacy cache: {cache_path}")
                    # Save to new cache format for future use
                    self._cache.save_sdg_embeddings(self._embeddings, self.model_name)
                    return self._embeddings
                except Exception as e:
                    print(f"Failed to load legacy cached embeddings: {e}")

        # Generate embeddings with multi-text approach
        print(f"Generating enhanced SDG embeddings using {self.model_name}...")
        print("Using multi-text embedding strategy (core + local_gov + indicators + keywords)")

        self._embeddings = {}

        for sdg_num in SDG_DEFINITIONS.keys():
            # Generate multiple text variants
            text_variants = self._generate_sdg_text_variants(sdg_num)

            # Encode each variant
            variant_embeddings = {}
            for variant_name, text in text_variants.items():
                embedding = self.model.encode(text, convert_to_numpy=True)
                variant_embeddings[variant_name] = embedding

            # Combine embeddings with weights
            combined_embedding = self._combine_embeddings(variant_embeddings)
            self._embeddings[sdg_num] = combined_embedding

            # Print progress for every 5 SDGs
            if sdg_num % 5 == 0:
                print(f"  Generated embeddings for {sdg_num}/17 SDGs...")

        print(f"Generated embeddings for all 17 SDGs")

        # Validate embeddings before caching
        if not self._embeddings:
            raise EmbeddingError("Failed to generate embeddings: embeddings dictionary is empty")

        if len(self._embeddings) != 17:
            raise EmbeddingError(
                f"Expected 17 SDG embeddings, but got {len(self._embeddings)}. "
                "SDG_DEFINITIONS may be incomplete."
            )

        # Cache embeddings using new efficient format
        try:
            cache_path = self._cache.save_sdg_embeddings(
                self._embeddings, self.model_name,
                metadata={"variant_weights": {"core": 0.35, "local_gov": 0.30, "indicators": 0.15, "keywords": 0.20}}
            )
            print(f"Embeddings cached to {cache_path}")
        except Exception as e:
            print(f"Failed to cache embeddings: {e}")

        return self._embeddings

    def get_embedding(self, sdg_num: int) -> np.ndarray:
        """Get embedding for a specific SDG."""
        if self._embeddings is None:
            self.generate_embeddings()
        return self._embeddings[sdg_num]

    def get_all_embeddings(self) -> Dict[int, np.ndarray]:
        """Get all SDG embeddings."""
        if self._embeddings is None:
            self.generate_embeddings()
        return self._embeddings

    def encode_text(self, text: str) -> np.ndarray:
        """Encode arbitrary text using the same model."""
        return self.model.encode(text, convert_to_numpy=True)

    def encode_texts(self, texts: List[str], batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
        """
        Encode multiple texts in batch using the same model.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar

        Returns:
            Array of embeddings (num_texts, embedding_dim)
        """
        if not texts:
            return np.array([])

        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

    def get_sdg_info(self, sdg_num: int) -> Dict[str, Any]:
        """Get full information about an SDG."""
        return SDG_DEFINITIONS.get(sdg_num, {})

    def get_sdg_name(self, sdg_num: int) -> str:
        """Get the name of an SDG."""
        return SDG_DEFINITIONS.get(sdg_num, {}).get("name", f"SDG {sdg_num}")

    def get_sdg_description(self, sdg_num: int) -> str:
        """Get the description of an SDG."""
        return SDG_DEFINITIONS.get(sdg_num, {}).get("description", "")

    def get_sdg_keywords(self, sdg_num: int, include_local_gov: bool = True) -> List[str]:
        """
        Get keywords for an SDG.

        Args:
            sdg_num: The SDG number
            include_local_gov: Whether to include local government specific keywords

        Returns:
            List of keywords
        """
        sdg = SDG_DEFINITIONS.get(sdg_num, {})
        keywords = list(sdg.get("keywords", []))

        if include_local_gov:
            local_keywords = sdg.get("local_gov_keywords", [])
            keywords.extend(local_keywords)

        return keywords

    def get_local_gov_keywords(self, sdg_num: int) -> List[str]:
        """Get local government specific keywords for an SDG."""
        return SDG_DEFINITIONS.get(sdg_num, {}).get("local_gov_keywords", [])

    def get_sdg_indicators(self, sdg_num: int) -> List[str]:
        """Get UN indicators for an SDG."""
        return SDG_DEFINITIONS.get(sdg_num, {}).get("indicators", [])

    def get_sdg_short_description(self, sdg_num: int) -> str:
        """Get the short description for an SDG."""
        return SDG_DEFINITIONS.get(sdg_num, {}).get("short_description", "")

    def get_sdg_color(self, sdg_num: int) -> str:
        """Get the official color for an SDG."""
        return SDG_DEFINITIONS.get(sdg_num, {}).get("color", "#000000")

    def get_all_sdgs(self) -> List[int]:
        """Get list of all SDG numbers."""
        return list(SDG_DEFINITIONS.keys())

    def get_sdg_text_for_display(self, sdg_num: int) -> str:
        """Get formatted text for display."""
        sdg = SDG_DEFINITIONS.get(sdg_num, {})
        return f"{sdg_num}. {sdg.get('name', '')}: {sdg.get('description', '')}"

    def clear_cache(self, include_legacy: bool = True) -> None:
        """
        Clear cached embeddings.

        Args:
            include_legacy: Also clear legacy cache files
        """
        # Clear new v2 cache
        stats = self._cache.clear_cache()
        print(f"Cleared cache: {stats['sdg']} SDG caches, {stats['activity']} activity caches")

        # Clear legacy cache if requested
        if include_legacy:
            legacy_path = self._get_legacy_cache_path()
            if legacy_path.exists():
                legacy_path.unlink()
                print(f"Cleared legacy cache: {legacy_path}")

        self._embeddings = None

    def get_embedding_info(self, sdg_num: int) -> Dict[str, Any]:
        """
        Get detailed information about an SDG's embedding components.

        Args:
            sdg_num: The SDG number

        Returns:
            Dictionary with text variants and their relative contributions
        """
        sdg = SDG_DEFINITIONS.get(sdg_num, {})
        variants = self._generate_sdg_text_variants(sdg_num)

        return {
            "sdg_number": sdg_num,
            "sdg_name": sdg.get("name", ""),
            "text_variants": {
                name: text[:200] + "..." if len(text) > 200 else text
                for name, text in variants.items()
            },
            "weights": {
                "core": 0.35,
                "local_gov": 0.30,
                "indicators": 0.15,
                "keywords": 0.20
            },
            "total_local_gov_keywords": len(sdg.get("local_gov_keywords", [])),
            "total_keywords": len(sdg.get("keywords", [])),
            "total_indicators": len(sdg.get("indicators", []))
        }

    def analyze_sdg_coverage(self) -> Dict[str, Any]:
        """
        Analyze the coverage of enhanced SDG definitions.

        Returns:
            Dictionary with coverage statistics
        """
        stats = {
            "sdgs_with_local_gov_keywords": 0,
            "sdgs_with_indicators": 0,
            "sdgs_with_short_description": 0,
            "total_local_gov_keywords": 0,
            "total_indicators": 0,
            "avg_local_gov_keywords_per_sdg": 0,
            "avg_indicators_per_sdg": 0
        }

        for sdg_num in SDG_DEFINITIONS.keys():
            sdg = SDG_DEFINITIONS[sdg_num]

            if sdg.get("local_gov_keywords"):
                stats["sdgs_with_local_gov_keywords"] += 1
                stats["total_local_gov_keywords"] += len(sdg["local_gov_keywords"])

            if sdg.get("indicators"):
                stats["sdgs_with_indicators"] += 1
                stats["total_indicators"] += len(sdg["indicators"])

            if sdg.get("short_description"):
                stats["sdgs_with_short_description"] += 1

        stats["avg_local_gov_keywords_per_sdg"] = (
            stats["total_local_gov_keywords"] / len(SDG_DEFINITIONS)
        )
        stats["avg_indicators_per_sdg"] = (
            stats["total_indicators"] / len(SDG_DEFINITIONS)
        )

        return stats

    def get_keyword_match_score(self, text: str, sdg_num: int) -> float:
        """
        Calculate simple keyword match score for baseline comparison.

        Args:
            text: Text to check
            sdg_num: SDG number

        Returns:
            Keyword match score (0-1)
        """
        keywords = self.get_sdg_keywords(sdg_num)
        if not keywords:
            return 0.0

        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)

        # Normalize by number of keywords
        return matches / len(keywords)
