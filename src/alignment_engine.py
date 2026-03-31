"""SDG Alignment Engine.

Computes semantic similarity between activities and SDGs using sentence transformers.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity

from src.sdg_reference import SDGReference
from src.config import Config
from src.embedding_cache import EmbeddingCache
from src.exceptions import EmbeddingError
from src.sdg17_bias_correction import apply_sdg17_corrections
from src.sdg11_bias_correction import apply_sdg11_corrections


class AlignmentEngine:
    """Compute SDG alignment scores for activities."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        enable_sdg17_correction: bool = True,
        sdg17_correction_method: str = "all",
        enable_sdg11_correction: bool = True,
        sdg11_correction_method: str = "all",
        custom_sdg_thresholds: Optional[Dict[int, float]] = None,
        use_custom_thresholds: bool = False
    ):
        """
        Initialize alignment engine.

        Args:
            model_name: Sentence transformer model name
            similarity_threshold: Minimum similarity for "relevant" classification
            enable_sdg17_correction: Whether to apply SDG 17 bias correction
            sdg17_correction_method: Method for SDG 17 correction ("multiplier", "reassign", "threshold", "negative", "all")
            enable_sdg11_correction: Whether to apply SDG 11 bias correction
            sdg11_correction_method: Method for SDG 11 correction ("multiplier", "reassign", "threshold", "negative", "all")
            custom_sdg_thresholds: Dict of SDG number -> threshold for custom thresholds
            use_custom_thresholds: Whether to use custom thresholds instead of defaults
        """
        self.config = Config()
        self.model_name = model_name or self.config.default_embedding_model
        self.similarity_threshold = similarity_threshold or self.config.get_similarity_threshold('st')

        # SDG 17 bias correction settings
        self.enable_sdg17_correction = enable_sdg17_correction
        self.sdg17_correction_method = sdg17_correction_method

        # SDG 11 bias correction settings
        self.enable_sdg11_correction = enable_sdg11_correction
        self.sdg11_correction_method = sdg11_correction_method

        # Custom threshold settings
        self.custom_sdg_thresholds = custom_sdg_thresholds or {}
        self.use_custom_thresholds = use_custom_thresholds

        self.sdg_reference = SDGReference(model_name=self.model_name)
        self._sdg_embeddings: Optional[Dict[int, np.ndarray]] = None
        self._sdg_embeddings_matrix: Optional[np.ndarray] = None
        self._sdg_numbers: Optional[List[int]] = None

        # Initialize activity embedding cache
        self._activity_cache = EmbeddingCache()

    def get_threshold_for_sdg(self, sdg_num: Optional[int] = None) -> float:
        """
        Get threshold for a specific SDG.

        Args:
            sdg_num: Optional SDG number (1-17). If None, returns global default.

        Returns:
            Optimized threshold for the SDG (or global default if SDG not specified)
        """
        # Use custom threshold if enabled
        if self.use_custom_thresholds and sdg_num and sdg_num in self.custom_sdg_thresholds:
            return self.custom_sdg_thresholds[sdg_num]

        return self.config.get_similarity_threshold('st', sdg=sdg_num)

    def set_threshold(self, threshold: float):
        """Set a custom threshold."""
        self.similarity_threshold = threshold

    def set_custom_thresholds(self, thresholds: Dict[int, float]):
        """Set custom thresholds per SDG."""
        self.custom_sdg_thresholds = thresholds
        self.use_custom_thresholds = True

    def _initialize_sdg_embeddings(self):
        """Pre-compute SDG embeddings matrix for batch processing."""
        if self._sdg_embeddings is None:
            self._sdg_embeddings = self.sdg_reference.get_all_embeddings()

            # Validate embeddings were loaded/generated successfully
            if not self._sdg_embeddings:
                raise EmbeddingError(
                    "Failed to initialize SDG embeddings. "
                    "The embeddings dictionary is empty. "
                    "Try clearing the cache with: "
                    "python -c \"from src.sdg_reference import SDGReference; SDGReference().clear_cache()\""
                )

            self._sdg_numbers = sorted(self._sdg_embeddings.keys())

            # Validate we have all 17 SDGs
            if len(self._sdg_numbers) != 17:
                raise EmbeddingError(
                    f"Expected 17 SDG embeddings, but got {len(self._sdg_numbers)}. "
                    f"SDGs found: {self._sdg_numbers}. "
                    "Try clearing the cache to regenerate embeddings."
                )

            # Stack embeddings into a matrix for vectorized computation
            self._sdg_embeddings_matrix = np.vstack([
                self._sdg_embeddings[num] for num in self._sdg_numbers
            ])

    def align_activity(
        self,
        activity_text: str,
        return_top_n: Optional[int] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Align a single activity with all SDGs.

        Args:
            activity_text: Activity description
            return_top_n: Return only top N SDGs (None for all)
            use_cache: Whether to use activity embedding cache

        Returns:
            Dictionary with scores for each SDG
        """
        # Get SDG embeddings
        self._initialize_sdg_embeddings()

        # Check cache first
        activity_embedding = None
        if use_cache:
            activity_embedding = self._activity_cache.get_activity_embedding(
                activity_text, self.model_name
            )

        # Encode activity if not in cache
        if activity_embedding is None:
            activity_embedding = self.sdg_reference.encode_text(activity_text)
            # Save to cache
            if use_cache:
                self._activity_cache.save_activity_embedding(
                    activity_text, self.model_name, activity_embedding
                )

        # Compute similarity with all SDGs at once (vectorized)
        # activity_embedding shape: (embedding_dim,)
        # _sdg_embeddings_matrix shape: (17, embedding_dim)
        # similarities shape: (17,)
        activity_vec = activity_embedding.reshape(1, -1)
        similarities = cosine_similarity(
            activity_vec,
            self._sdg_embeddings_matrix
        )[0]  # Shape: (17,)

        # Build scores dict from vectorized results
        scores = {}
        for i, sdg_num in enumerate(self._sdg_numbers):
            similarity = float(similarities[i])
            # Always use optimized threshold from threshold_config.py
            # custom_sdg_thresholds only for manual overrides
            threshold = self.get_threshold_for_sdg(sdg_num)
            scores[sdg_num] = {
                "score": round(similarity, 4),
                "is_aligned": similarity >= threshold,
                "sdg_name": self.sdg_reference.get_sdg_name(sdg_num),
                "threshold_used": threshold
            }

        # Apply SDG 17 bias correction if enabled
        if self.enable_sdg17_correction:
            scores = apply_sdg17_corrections(
                activity_text,
                scores,
                correction_method=self.sdg17_correction_method
            )

        # Apply SDG 11 bias correction if enabled
        if self.enable_sdg11_correction:
            scores = apply_sdg11_corrections(
                activity_text,
                scores,
                activity_metadata=None,
                correction_method=self.sdg11_correction_method
            )

        # Find top SDG
        top_sdg = max(scores.keys(), key=lambda k: scores[k]["score"])

        result = {
            "activity_text": activity_text,
            "word_count": len(activity_text.split()),
            "sdg_scores": scores,
            "top_sdg": top_sdg,
            "top_sdg_name": scores[top_sdg]["sdg_name"],
            "top_score": scores[top_sdg]["score"],
            "num_aligned": sum(1 for s in scores.values() if s["is_aligned"])
        }

        # Sort SDGs by score
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        # Return only top N if requested
        if return_top_n:
            result["top_sdgs"] = [
                {"sdg": sdg, "name": data["sdg_name"], "score": data["score"]}
                for sdg, data in sorted_scores[:return_top_n]
            ]

        return result

    def align_activities(
        self,
        activities: List[Dict[str, Any]],
        show_progress: bool = True,
        batch_size: int = 32,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Align multiple activities with SDGs using batch processing.

        Args:
            activities: List of activity dictionaries
            show_progress: Whether to show progress bar
            batch_size: Batch size for encoding
            use_cache: Whether to use activity embedding cache

        Returns:
            List of activity alignment results
        """
        if not activities:
            return []

        # Initialize SDG embeddings once
        self._initialize_sdg_embeddings()

        # Filter valid activities and extract texts
        valid_activities = []
        texts = []
        for activity in activities:
            text = activity.get("text", "")
            if text:
                valid_activities.append(activity)
                texts.append(text)

        if not texts:
            return []

        # Check cache for existing embeddings
        if use_cache:
            cached_embeddings, cache_misses = self._activity_cache.get_activity_embeddings_batch(
                texts, self.model_name
            )
            cache_hits = len(texts) - len(cache_misses)
            if show_progress and cache_hits > 0:
                print(f"Cache: {cache_hits}/{len(texts)} activities loaded from cache")
        else:
            cached_embeddings = [None] * len(texts)
            cache_misses = list(range(len(texts)))

        # Collect texts that need encoding (cache misses)
        texts_to_encode = [texts[i] for i in cache_misses]

        activity_embeddings = np.zeros((len(texts), self._sdg_embeddings_matrix.shape[1]))

        # Fill in cached embeddings
        for i, emb in enumerate(cached_embeddings):
            if emb is not None:
                activity_embeddings[i] = emb

        # Encode cache misses in batch
        if texts_to_encode:
            if show_progress:
                print(f"Encoding {len(texts_to_encode)} new activities in batches of {batch_size}...")

            new_embeddings = self.sdg_reference.encode_texts(
                texts_to_encode,
                batch_size=batch_size,
                show_progress=show_progress
            )

            # Fill in new embeddings
            for idx, new_emb in zip(cache_misses, new_embeddings):
                activity_embeddings[idx] = new_emb

            # Save new embeddings to cache
            if use_cache:
                self._activity_cache.save_activity_embeddings_batch(
                    texts_to_encode, self.model_name, new_embeddings
                )

        # Compute cosine similarities in batch using sklearn
        # similarities shape: (num_activities, num_sdgs)
        similarities = cosine_similarity(
            activity_embeddings,
            self._sdg_embeddings_matrix
        )

        # Build results
        results = []
        iterator = tqdm(range(len(valid_activities)), disable=not show_progress)

        for idx in iterator:
            activity = valid_activities[idx]
            sim_row = similarities[idx]

            # Build scores dict
            scores = {}
            for i, sdg_num in enumerate(self._sdg_numbers):
                similarity = float(sim_row[i])
                # Always use optimized threshold from threshold_config.py
                # custom_sdg_thresholds only for manual overrides
                threshold = self.get_threshold_for_sdg(sdg_num)
                scores[sdg_num] = {
                    "score": round(similarity, 4),
                    "is_aligned": similarity >= threshold,
                    "sdg_name": self.sdg_reference.get_sdg_name(sdg_num),
                    "threshold_used": threshold
                }

            # Apply SDG 17 bias correction if enabled
            if self.enable_sdg17_correction:
                scores = apply_sdg17_corrections(
                    texts[idx],
                    scores,
                    correction_method=self.sdg17_correction_method
                )

            # Apply SDG 11 bias correction if enabled
            if self.enable_sdg11_correction:
                scores = apply_sdg11_corrections(
                    texts[idx],
                    scores,
                    activity_metadata=None,
                    correction_method=self.sdg11_correction_method
                )

            # Find top SDG
            top_sdg = max(scores.keys(), key=lambda k: scores[k]["score"])

            alignment = {
                "activity_text": texts[idx],
                "word_count": len(texts[idx].split()),
                "sdg_scores": scores,
                "top_sdg": top_sdg,
                "top_sdg_name": scores[top_sdg]["sdg_name"],
                "top_score": scores[top_sdg]["score"],
                "num_aligned": sum(1 for s in scores.values() if s["is_aligned"])
            }

            # Merge with original activity data
            result = {**activity, **alignment}
            results.append(result)

        return results

    def compute_report_alignment(
        self,
        activity_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute aggregate alignment scores for a report.

        Args:
            activity_results: List of activity alignment results

        Returns:
            Report-level alignment statistics
        """
        if not activity_results:
            return {
                "total_activities": 0,
                "mean_scores": {},
                "coverage": {},
                "top_sdgs": []
            }

        total = len(activity_results)

        # Compute mean scores per SDG
        mean_scores = {}
        for sdg_num in range(1, 18):
            scores = [
                r["sdg_scores"][sdg_num]["score"]
                for r in activity_results
                if sdg_num in r.get("sdg_scores", {})
            ]
            mean_scores[sdg_num] = round(sum(scores) / len(scores), 4) if scores else 0.0

        # Compute coverage (percentage of activities mentioning each SDG)
        coverage = {}
        for sdg_num in range(1, 18):
            aligned = sum(
                1 for r in activity_results
                if r.get("sdg_scores", {}).get(sdg_num, {}).get("is_aligned", False)
            )
            coverage[sdg_num] = round(aligned / total, 4) if total > 0 else 0.0

        # Find top SDGs by mean score
        sorted_sdgs = sorted(
            mean_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_sdgs = [
            {
                "sdg": sdg,
                "name": self.sdg_reference.get_sdg_name(sdg),
                "mean_score": score,
                "coverage": coverage[sdg]
            }
            for sdg, score in sorted_sdgs
        ]

        # Calculate overall alignment score
        overall_score = sum(mean_scores.values()) / len(mean_scores) if mean_scores else 0.0

        # Gap analysis - SDGs with low/no coverage
        gap_sdgs = [s for s in top_sdgs if s["coverage"] == 0]

        return {
            "total_activities": total,
            "mean_alignment_score": round(overall_score, 4),
            "mean_scores": mean_scores,
            "coverage": coverage,
            "top_sdgs": top_sdgs,
            "gaps": gap_sdgs
        }

    def compare_activities(
        self,
        activity1: str,
        activity2: str
    ) -> float:
        """
        Compare two activities for similarity.

        Args:
            activity1: First activity text
            activity2: Second activity text

        Returns:
            Similarity score
        """
        emb1 = self.sdg_reference.encode_text(activity1)
        emb2 = self.sdg_reference.encode_text(activity2)
        return float(cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0, 0])

    def find_similar_activities(
        self,
        query: str,
        activities: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find activities most similar to a query.

        Args:
            query: Search query
            activities: List of activity texts
            top_k: Number of results to return

        Returns:
            List of (activity, score) tuples
        """
        if not activities:
            return []

        # Encode query once
        query_emb = self.sdg_reference.encode_text(query)

        # Batch encode all activities (vectorized)
        activity_embeddings = self.sdg_reference.encode_texts(activities, show_progress=False)

        # Compute all similarities at once (vectorized)
        # query_emb shape: (embedding_dim,)
        # activity_embeddings shape: (n_activities, embedding_dim)
        similarities = cosine_similarity(
            query_emb.reshape(1, -1),
            activity_embeddings
        )[0]  # Shape: (n_activities,)

        # Build results and sort
        results = [
            (activity, float(similarities[i]))
            for i, activity in enumerate(activities)
        ]
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def align_report(
        self,
        activities_data: Dict[str, Any],
        show_progress: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Process a full report and compute SDG alignment.

        Args:
            activities_data: Output from ActivityExtractor
            show_progress: Whether to show progress bar
            use_cache: Whether to use activity embedding cache

        Returns:
            Full alignment results with activities and summary
        """
        activities = activities_data.get("activities", [])

        # Align all activities
        aligned_activities = self.align_activities(activities, show_progress, use_cache=use_cache)

        # Compute report-level statistics
        report_alignment = self.compute_report_alignment(aligned_activities)

        # Get all SDG-specific thresholds for config output
        all_thresholds = self.config.get_all_similarity_thresholds('st')

        return {
            "source": activities_data.get("source", ""),
            "metadata": activities_data.get("metadata", {}),
            "alignment_config": {
                "model": self.model_name,
                "similarity_threshold": self.similarity_threshold,
                "threshold_mode": "sdg_specific",
                "sdg_specific_thresholds": all_thresholds,
                "sdg17_correction": {
                    "enabled": self.enable_sdg17_correction,
                    "method": self.sdg17_correction_method
                }
            },
            "activities": aligned_activities,
            "report_alignment": report_alignment
        }

    def batch_align_reports(
        self,
        reports_data: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process multiple reports.

        Args:
            reports_data: List of ActivityExtractor outputs
            show_progress: Whether to show progress bar

        Returns:
            List of alignment results
        """
        results = []
        iterator = tqdm(reports_data, desc="Processing reports") if show_progress else reports_data

        for report_data in iterator:
            result = self.align_report(report_data, show_progress=False)
            results.append(result)

        return results

    def get_alignment_matrix(
        self,
        results: Dict[str, Any]
    ) -> np.ndarray:
        """
        Get alignment matrix as numpy array (activities x SDGs).

        Args:
            results: Alignment results from align_report

        Returns:
            Numpy array of shape (n_activities, 17)
        """
        activities = results.get("activities", [])
        if not activities:
            return np.array([])

        matrix = np.zeros((len(activities), 17))
        for i, activity in enumerate(activities):
            for sdg_num in range(1, 18):
                score = activity.get("sdg_scores", {}).get(sdg_num, {}).get("score", 0)
                matrix[i, sdg_num - 1] = score

        return matrix

    def export_to_csv(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Export alignment results to CSV."""
        import pandas as pd

        activities = results.get("activities", [])
        if not activities:
            return

        rows = []
        for activity in activities:
            row = {
                "activity_text": activity["activity_text"],
                "word_count": activity["word_count"],
                "top_sdg": activity["top_sdg"],
                "top_sdg_name": activity["top_sdg_name"],
                "top_score": activity["top_score"],
                "num_aligned": activity["num_aligned"]
            }
            # Add all SDG scores
            for sdg_num in range(1, 18):
                row[f"sdg_{sdg_num}_score"] = activity["sdg_scores"][sdg_num]["score"]

            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

    def export_to_json(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Export alignment results to JSON."""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
