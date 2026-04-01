"""Hybrid Alignment Engine with sdgBERT Support.

Extends the standard AlignmentEngine with optional sdgBERT classifier integration.
Provides ensemble capabilities combining sentence transformers and BERT-based classification.

Reference:
- sdgBERT: https://huggingface.co/sadickam/sdgBERT
- Paper: Sadick et al. (2026), Journal of Construction Engineering and Management
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import warnings

import numpy as np
from tqdm import tqdm

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier
from src.sdg_reference import SDGReference
from src.config import Config
from src.sdg_ensemble_weights import SDG_ENSEMBLE_WEIGHTS, DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT
from src.sdg17_bias_correction import (
    apply_sdg17_corrections,
    recalculate_top_sdg,
    contains_local_keywords,
    contains_true_sdg17_keywords
)
from src.sdg11_bias_correction import apply_sdg11_corrections
from src.sdg14_bias_correction import apply_sdg14_corrections
from src.sdg4_bias_correction import apply_sdg4_corrections
from src.sdg6_bias_correction import apply_sdg6_corrections
from src.sdg8_bias_correction import apply_sdg8_corrections
from src.sdg10_bias_correction import apply_sdg10_corrections
from src.sdg12_bias_correction import apply_sdg12_corrections
from src.sdg16_bias_correction import apply_sdg16_corrections
from src.exceptions import ModelLoadError

logger = logging.getLogger(__name__)


# SDG-specific keyword boosters for underrepresented SDGs
SDG_KEYWORD_BOOSTS = {
    3: {
        # Good Health and Well-being
        "keywords": ["health", "medical", "wellbeing", "well-being", "caps", "early intervention", "mental health", "healthcare"],
        "boost": 0.20  # Increased from 0.15
    },
    12: {
        # Responsible Consumption and Production
        "keywords": ["waste", "recycling", "recycle", "depot", "reuse", "sustainable consumption", "circular economy", "waste management"],
        "boost": 0.20  # Increased from 0.15
    },
    13: {
        # Climate Action
        "keywords": ["emissions", "carbon", "climate action", "renewable energy", "solar", "wind power", "greenhouse"],
        "boost": 0.20  # Increased from 0.15
    },
    14: {
        # Life Below Water
        "keywords": ["marine", "ocean", "fisheries", "coastal", "water pollution", "sea"],
        "boost": 0.20  # Increased from 0.15
    },
    16: {
        # Peace, Justice and Strong Institutions
        "keywords": ["governance", "transparency", "accountability", "internal review",
                     "business continuity", "audit", "financial statements", "councillor",
                     "ethics", "code of conduct", "anti-corruption", "disclosure"],
        "boost": 0.25  # Higher boost to improve SDG 16 detection
    },
}


def apply_keyword_boost(activity_text: str, sdg_scores: Dict[int, Dict[str, Any]], debug: bool = False) -> Dict[int, Dict[str, Any]]:
    """
    Apply keyword-based boosting to SDG scores for underrepresented SDGs.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        debug: Print debug information

    Returns:
        Updated SDG scores with keyword boosts applied
    """
    text_lower = activity_text.lower()

    for sdg_num, config in SDG_KEYWORD_BOOSTS.items():
        # Skip SDG 14 if bias correction was already applied
        # (correction indicates road names, place names, or infrastructure - not marine)
        if sdg_num == 14 and sdg_scores.get(14, {}).get("correction_applied", False):
            if debug:
                print(f"   [BOOST DEBUG] SDG 14: Skipping keyword boost - bias correction already applied")
            continue

        # Check if any keywords are present
        has_keyword = any(kw.lower() in text_lower for kw in config["keywords"])

        if has_keyword and sdg_num in sdg_scores:
            # Apply boost but cap at 1.0
            current_score = sdg_scores[sdg_num]['score']
            boosted_score = min(current_score + config["boost"], 1.0)
            sdg_scores[sdg_num]['score'] = boosted_score

            # Update is_aligned status based on threshold
            sdg_scores[sdg_num]['is_aligned'] = boosted_score >= 0.3  # Lower threshold for keyword-matched

            if debug:
                print(f"   [BOOST DEBUG] SDG {sdg_num}: {current_score:.3f} -> {boosted_score:.3f}")

    return sdg_scores


class HybridAlignmentEngine(AlignmentEngine):
    """
    Hybrid SDG Alignment Engine supporting both Sentence Transformer and sdgBERT.
    
    This engine extends the standard AlignmentEngine with optional integration of
    the sadickam/sdgBERT model for improved classification accuracy.
    
    Performance Comparison:
    - Sentence Transformer (fine-tuned): 87.6% accuracy
    - sdgBERT: 90.0% accuracy
    - Ensemble (both): Expected 90-92% accuracy
    
    Reference:
        Sadick, A.-M., Hasan, A. and Ahiaga-Dagbui, D.D. (2026),
        "Modeling sustainability discourse in the construction industry: 
        A deep-learning approach". Journal of Construction Engineering and 
        Management, 152(4). DOI: 10.1061/JCEMD4.COENG-16205
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        use_sdg_bert: bool = False,
        sdg_bert_model: Optional[str] = None,
        ensemble_mode: str = "weighted",  # "weighted", "fallback", "single"
        sdg_bert_weight: float = 0.55,
        st_weight: float = 0.45,
        fallback_threshold: float = 0.5,
        enable_sdg17_correction: bool = True,
        sdg17_correction_method: str = "all",
        enable_sdg11_correction: bool = True,
        sdg11_correction_method: str = "all",
        enable_sdg14_correction: bool = True,
        sdg14_correction_method: str = "all",
        enable_sdg4_correction: bool = True,
        sdg4_correction_method: str = "all",
        enable_sdg6_correction: bool = True,
        sdg6_correction_method: str = "all",
        enable_sdg8_correction: bool = True,
        sdg8_correction_method: str = "all",
        enable_sdg10_correction: bool = True,
        sdg10_correction_method: str = "all",
        enable_sdg12_correction: bool = True,
        sdg12_correction_method: str = "all",
        enable_sdg16_correction: bool = True,
        sdg16_correction_method: str = "all",
        custom_sdg_thresholds: Optional[Dict[int, float]] = None,
        use_custom_thresholds: bool = False
    ):
        """
        Initialize hybrid alignment engine.

        Args:
            model_name: Sentence transformer model name
            similarity_threshold: Minimum similarity for "relevant" classification
                                  Default: 0.7 for hybrid (normalized 0-1 scale), 0.3 for ST-only
            use_sdg_bert: Whether to load sdgBERT classifier
            sdg_bert_model: HuggingFace model name for sdgBERT (default: sadickam/sdgBERT)
            ensemble_mode: How to combine models ("weighted", "fallback", "single")
            sdg_bert_weight: Weight for sdgBERT in ensemble (default: 0.55)
            st_weight: Weight for Sentence Transformer in ensemble (default: 0.45)
            fallback_threshold: Threshold for fallback mode
            enable_sdg17_correction: Whether to apply SDG 17 bias correction
            sdg17_correction_method: Method for SDG 17 correction
            enable_sdg11_correction: Whether to apply SDG 11 bias correction
            sdg11_correction_method: Method for SDG 11 correction
            enable_sdg14_correction: Whether to apply SDG 14 bias correction
            sdg14_correction_method: Method for SDG 14 correction
            enable_sdg4_correction: Whether to apply SDG 4 bias correction
            sdg4_correction_method: Method for SDG 4 correction
            enable_sdg6_correction: Whether to apply SDG 6 bias correction
            sdg6_correction_method: Method for SDG 6 correction
            enable_sdg8_correction: Whether to apply SDG 8 bias correction
            sdg8_correction_method: Method for SDG 8 correction
            enable_sdg10_correction: Whether to apply SDG 10 bias correction
            sdg10_correction_method: Method for SDG 10 correction
            enable_sdg12_correction: Whether to apply SDG 12 bias correction
            sdg12_correction_method: Method for SDG 12 correction
            enable_sdg16_correction: Whether to apply SDG 16 bias correction
            sdg16_correction_method: Method for SDG 16 correction
            custom_sdg_thresholds: Dict of SDG number -> threshold for custom thresholds
            use_custom_thresholds: Whether to use custom thresholds instead of defaults
        """
        # Save parameters before parent init
        self.use_sdg_bert = use_sdg_bert
        self.enable_sdg4_correction = enable_sdg4_correction
        self.sdg4_correction_method = sdg4_correction_method
        self.enable_sdg6_correction = enable_sdg6_correction
        self.sdg6_correction_method = sdg6_correction_method
        self.enable_sdg8_correction = enable_sdg8_correction
        self.sdg8_correction_method = sdg8_correction_method
        self.enable_sdg10_correction = enable_sdg10_correction
        self.sdg10_correction_method = sdg10_correction_method
        self.enable_sdg12_correction = enable_sdg12_correction
        self.sdg12_correction_method = sdg12_correction_method
        self.enable_sdg16_correction = enable_sdg16_correction
        self.sdg16_correction_method = sdg16_correction_method

        # Initialize parent class first
        super().__init__(
            model_name, similarity_threshold,
            enable_sdg17_correction=enable_sdg17_correction,
            sdg17_correction_method=sdg17_correction_method,
            enable_sdg11_correction=enable_sdg11_correction,
            sdg11_correction_method=sdg11_correction_method,
            custom_sdg_thresholds=custom_sdg_thresholds,
            use_custom_thresholds=use_custom_thresholds
        )

        # Store additional correction settings (not passed to parent)
        self.enable_sdg14_correction = enable_sdg14_correction
        self.sdg14_correction_method = sdg14_correction_method

        # Set default threshold using optimized configuration (if not provided)
        if similarity_threshold is None:
            if self.use_sdg_bert:
                self.similarity_threshold = self.config.get_similarity_threshold('hybrid')
            else:
                self.similarity_threshold = self.config.get_similarity_threshold('st')

        # sdgBERT configuration
        self.use_sdg_bert = use_sdg_bert
        self.ensemble_mode = ensemble_mode
        self.sdg_bert_weight = sdg_bert_weight
        self.st_weight = st_weight
        self.fallback_threshold = fallback_threshold

        # Load sdgBERT if requested
        self.sdg_bert = None
        self._sdg_bert_load_error = None

        if use_sdg_bert:
            try:
                logger.info("Initializing sdgBERT classifier...")
                self.sdg_bert = SDGBERTClassifier(model_name=sdg_bert_model)
                logger.info(f"✓ Hybrid engine ready (mode: {ensemble_mode}, sdgBERT loaded)")
            except Exception as e:
                logger.error(f"sdgBERT load failed: {e}", exc_info=True)
                self.use_sdg_bert = False
                self.ensemble_mode = "single"  # Reset mode to match capability
                self._sdg_bert_load_error = str(e)
                warnings.warn(f"Failed to load sdgBERT: {e}. Falling back to Sentence Transformer only.")

    def get_threshold(self, sdg_num: Optional[int] = None) -> float:
        """
        Get optimized threshold for hybrid mode.

        Args:
            sdg_num: Optional SDG number (1-17). If None, returns global hybrid default.

        Returns:
            Optimized threshold for hybrid mode (or SDG-specific if sdg_num provided)
        """
        return self.get_threshold_for_sdg(sdg_num)

    def get_threshold_for_sdg(self, sdg_num: Optional[int] = None) -> float:
        """
        Get optimized threshold for a specific SDG in hybrid mode.

        Args:
            sdg_num: Optional SDG number (1-17). If None, returns global hybrid default.

        Returns:
            Optimized threshold for the SDG in hybrid mode
        """
        return self.config.get_similarity_threshold('hybrid', sdg=sdg_num)

    def _compute_sentence_transformer_scores(self, activity_text: str) -> Dict[str, Any]:
        """Compute Sentence Transformer scores for a single activity."""
        return super().align_activity(activity_text, return_top_n=None)

    def _get_sdg_weights(self, sdg_num: int) -> Tuple[float, float]:
        """
        Get ensemble weights for a specific SDG.

        Returns:
            Tuple of (sdg_bert_weight, st_weight)
        """
        if hasattr(self, '_custom_sdg_weights') and sdg_num in self._custom_sdg_weights:
            return self._custom_sdg_weights[sdg_num]
        return SDG_ENSEMBLE_WEIGHTS.get(sdg_num, (DEFAULT_SDG_BERT_WEIGHT, DEFAULT_ST_WEIGHT))

    def set_sdg_weights(self, sdg_num: int, sdg_bert_weight: float, st_weight: float):
        """
        Set custom weights for a specific SDG (for grid search).

        Args:
            sdg_num: SDG number (1-17)
            sdg_bert_weight: Weight for sdgBERT
            st_weight: Weight for Sentence Transformer
        """
        if not hasattr(self, '_custom_sdg_weights'):
            self._custom_sdg_weights = {}
        self._custom_sdg_weights[sdg_num] = (sdg_bert_weight, st_weight)

    def clear_custom_weights(self):
        """Clear custom SDG weights and revert to defaults."""
        if hasattr(self, '_custom_sdg_weights'):
            del self._custom_sdg_weights

    def _combine_scores(
        self,
        st_scores: Dict[int, Dict[str, Any]],
        sdg_bert_pred: Dict[str, Any]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Combine Sentence Transformer and sdgBERT scores using ensemble mode.

        Args:
            st_scores: Sentence Transformer scores dict
            sdg_bert_pred: sdgBERT prediction dict with 'sdg', 'confidence', 'all_scores'

        Returns:
            Combined scores dict
        """
        combined = {}

        if self.ensemble_mode == "weighted":
            for sdg_num in range(1, 18):
                # Get SDG-specific weights
                sdg_bert_weight, st_weight = self._get_sdg_weights(sdg_num)

                # Get ST score and normalize
                st_score_raw = st_scores[sdg_num]['score']
                st_score = min(st_score_raw / 0.6, 1.0)

                # Get sdgBERT score
                sdg_bert_score = sdg_bert_pred['all_scores'].get(sdg_num, 0)

                # Weighted combination using SDG-specific weights
                ensemble_score = (
                    sdg_bert_weight * sdg_bert_score +
                    st_weight * st_score
                )

                combined[sdg_num] = {
                    'score': ensemble_score,
                    'is_aligned': ensemble_score >= self.get_threshold(sdg_num),
                    'sdg_name': self.sdg_reference.get_sdg_name(sdg_num)
                }
        else:
            # For other modes, just use ST scores as base
            combined = st_scores.copy()

        return combined

    def align_activity(
        self,
        activity_text: str,
        return_top_n: Optional[int] = None,
        use_ensemble: bool = True
    ) -> Dict[str, Any]:
        """
        Align a single activity with all SDGs using hybrid approach.
        
        Args:
            activity_text: Activity description
            return_top_n: Return only top N SDGs (None for all)
            use_ensemble: Whether to use ensemble prediction if available
            
        Returns:
            Dictionary with scores for each SDG and model predictions
        """
        # Get base sentence transformer result
        st_result = super().align_activity(activity_text, return_top_n=None)

        # Apply keyword boosting for underrepresented SDGs (SDG 3, 12, 13, 14)
        # This happens BEFORE the early return so all paths get the boost
        st_result['sdg_scores'] = apply_keyword_boost(activity_text, st_result['sdg_scores'])

        # Recalculate num_aligned after keyword boost
        st_result["num_aligned"] = sum(
            1 for s in st_result["sdg_scores"].values() if s["is_aligned"]
        )

        # Re-determine top SDG after keyword boost
        top_sdg = max(st_result['sdg_scores'].items(), key=lambda x: x[1]['score'])
        st_result['top_sdg'] = top_sdg[0]
        st_result['top_score'] = top_sdg[1]['score']
        st_result['top_sdg_name'] = top_sdg[1]['sdg_name']

        # If sdgBERT not enabled, return ST result (with keyword boost already applied)
        if not self.use_sdg_bert or not self.sdg_bert:
            return st_result

        # Get sdgBERT prediction
        sdg_bert_result = self.sdg_bert.predict(activity_text, return_all_scores=True)
        
        # Combine results based on mode
        if self.ensemble_mode == "weighted" and use_ensemble:
            # Calculate ensemble scores directly with SDG-specific weights
            ensemble_scores = {}
            for sdg_num in range(1, 18):
                # Get SDG-specific weights
                sdg_bert_weight, st_weight = self._get_sdg_weights(sdg_num)

                # Get ST score (already calculated)
                st_score_raw = st_result['sdg_scores'][sdg_num]['score']
                # Normalize ST score (assume max ~0.6)
                st_score = min(st_score_raw / 0.6, 1.0)

                # Get sdgBERT score
                sdg_bert_score = sdg_bert_result['all_scores'].get(sdg_num, 0)

                # Weighted combination using SDG-specific weights
                ensemble_scores[sdg_num] = (
                    sdg_bert_weight * sdg_bert_score +
                    st_weight * st_score
                )

            # Find top SDG from ensemble
            ensemble_top_sdg = max(ensemble_scores.keys(), key=lambda k: ensemble_scores[k])
            ensemble_top_score = ensemble_scores[ensemble_top_sdg]

            # Update all scores with ensemble scores
            for sdg_num in range(1, 18):
                st_result['sdg_scores'][sdg_num]['score'] = ensemble_scores[sdg_num]
                st_result['sdg_scores'][sdg_num]['is_aligned'] = (
                    ensemble_scores[sdg_num] >= self.get_threshold(sdg_num)
                )

            # Update top SDG
            st_result['top_sdg'] = ensemble_top_sdg
            st_result['top_score'] = ensemble_top_score
            st_result['top_sdg_name'] = self.sdg_reference.get_sdg_name(ensemble_top_sdg)

            # Get ST's original top prediction (before ensemble)
            st_original_top = st_result['top_sdg']

            # Check for model agreement
            models_agree = (st_original_top == sdg_bert_result['sdg'])

            # Add model comparison info
            st_result["model_predictions"] = {
                "sentence_transformer": {
                    "sdg": st_original_top,
                    "score": st_result['top_score']
                },
                "sdg_bert": {
                    "sdg": sdg_bert_result['sdg'],
                    "confidence": sdg_bert_result['confidence']
                },
                "models_agree": models_agree,
            }

        elif self.ensemble_mode == "fallback":
            # Use fallback strategy
            st_score = st_result["top_score"]
            
            if st_score < self.fallback_threshold:
                # Trust sdgBERT when ST is uncertain
                sdg_bert_sdg = sdg_bert_result["sdg"]
                
                # Update to sdgBERT prediction
                st_result["top_sdg"] = sdg_bert_sdg
                st_result["top_sdg_name"] = self.sdg_reference.get_sdg_name(sdg_bert_sdg)
                st_result["top_score"] = sdg_bert_result["confidence"]
                st_result["primary_model"] = "sdg_bert"
                
                # Update all scores to sdgBERT probabilities
                for sdg_num in range(1, 18):
                    if sdg_num in st_result["sdg_scores"]:
                        prob = sdg_bert_result["all_scores"].get(sdg_num, 0)
                        st_result["sdg_scores"][sdg_num]["score"] = prob
                        st_result["sdg_scores"][sdg_num]["is_aligned"] = prob >= self.get_threshold(sdg_num)
            else:
                st_result["primary_model"] = "sentence_transformer"
            
            st_result["sdg_bert_prediction"] = sdg_bert_result
            
        else:  # "single" mode - keep both but use ST as primary
            st_result["sdg_bert_prediction"] = sdg_bert_result

        # Apply SDG 17 bias correction if enabled
        if self.enable_sdg17_correction:
            st_result['sdg_scores'] = apply_sdg17_corrections(
                activity_text,
                st_result['sdg_scores'],
                correction_method=self.sdg17_correction_method
            )

        # Apply SDG 11 bias correction if enabled
        if self.enable_sdg11_correction:
            st_result['sdg_scores'] = apply_sdg11_corrections(
                activity_text,
                st_result['sdg_scores'],
                activity_metadata=None,
                correction_method=self.sdg11_correction_method
            )

        # Apply SDG 14 bias correction if enabled (after ensemble to catch sdgBERT predictions)
        if self.enable_sdg14_correction:
            st_result['sdg_scores'] = apply_sdg14_corrections(
                activity_text,
                st_result['sdg_scores'],
                activity_metadata=None,
                correction_method=self.sdg14_correction_method
            )

        # Apply SDG 4 bias correction if enabled
        if self.enable_sdg4_correction:
            st_result['sdg_scores'] = apply_sdg4_corrections(
                activity_text,
                st_result['sdg_scores'],
                correction_method=self.sdg4_correction_method
            )

        # Apply SDG 6 bias correction if enabled
        if self.enable_sdg6_correction:
            st_result['sdg_scores'] = apply_sdg6_corrections(
                activity_text,
                st_result['sdg_scores'],
                correction_method=self.sdg6_correction_method
            )

        # Apply SDG 8 bias correction if enabled
        if self.enable_sdg8_correction:
            st_result['sdg_scores'] = apply_sdg8_corrections(
                activity_text,
                st_result['sdg_scores'],
                correction_method=self.sdg8_correction_method
            )

        # Apply SDG 10 bias correction if enabled
        if self.enable_sdg10_correction:
            st_result['sdg_scores'] = apply_sdg10_corrections(
                activity_text,
                st_result['sdg_scores'],
                correction_method=self.sdg10_correction_method
            )

        # Apply SDG 12 bias correction if enabled
        if self.enable_sdg12_correction:
            st_result['sdg_scores'] = apply_sdg12_corrections(
                activity_text,
                st_result['sdg_scores'],
                correction_method=self.sdg12_correction_method
            )

        # Apply SDG 16 bias correction if enabled
        if self.enable_sdg16_correction:
            st_result['sdg_scores'] = apply_sdg16_corrections(
                activity_text,
                st_result['sdg_scores'],
                correction_method=self.sdg16_correction_method
            )

        # Recalculate num_aligned after all processing
        st_result["num_aligned"] = sum(
            1 for s in st_result["sdg_scores"].values() if s["is_aligned"]
        )

        # Re-determine top SDG after all processing
        top_sdg = max(st_result['sdg_scores'].items(), key=lambda x: x[1]['score'])
        st_result['top_sdg'] = top_sdg[0]
        st_result['top_score'] = top_sdg[1]['score']
        st_result['top_sdg_name'] = top_sdg[1]['sdg_name']

        # Return only top N if requested
        if return_top_n:
            sorted_scores = sorted(
                st_result["sdg_scores"].items(),
                key=lambda x: x[1]["score"],
                reverse=True
            )
            st_result["top_sdgs"] = [
                {"sdg": sdg, "name": data["sdg_name"], "score": data["score"]}
                for sdg, data in sorted_scores[:return_top_n]
            ]
        
        return st_result
    
    def align_activities(
        self,
        activities: List[Dict[str, Any]],
        show_progress: bool = True,
        use_ensemble: bool = True,
        batch_size: int = 32,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Align multiple activities with SDGs using hybrid approach.

        Uses batch processing for better performance. When sdgBERT is enabled,
        it uses sdgBERT's batch prediction for efficiency.

        Args:
            activities: List of activity dictionaries
            show_progress: Whether to show progress bar
            use_ensemble: Whether to use ensemble prediction
            batch_size: Batch size for encoding

        Returns:
            List of activity alignment results
        """
        if not activities:
            return []

        # If not using sdgBERT, use the parent's batch processing
        if not self.use_sdg_bert:
            return super().align_activities(activities, show_progress, batch_size)

        # When using sdgBERT, process with batching
        results = []

        # Filter valid activities
        valid_activities = []
        texts = []
        for activity in activities:
            text = activity.get("text", "")
            if text:
                valid_activities.append(activity)
                texts.append(text)

        if not texts:
            return []

        # Batch process with sdgBERT if available
        if self.sdg_bert and len(texts) > 1:
            try:
                if show_progress:
                    print(f"Processing {len(texts)} activities with batch prediction (ST + sdgBERT)...")

                # Calculate average text length for debugging
                avg_len = sum(len(t) for t in texts) / len(texts) if texts else 0
                print(f"  Average text length: {avg_len:.0f} chars")

                # BATCH: Get Sentence Transformer embeddings for ALL texts at once
                if show_progress:
                    print(f"  Computing ST embeddings for {len(texts)} activities...")
                # Initialize SDG embeddings first
                self._initialize_sdg_embeddings()
                # Use sdg_reference for batch encoding
                st_embeddings = self.sdg_reference.encode_texts(texts, show_progress=show_progress)

                if show_progress:
                    print(f"  Computing ST similarity scores...")
                # Compute ST similarity scores for all embeddings at once
                all_st_scores = []
                for emb in tqdm(st_embeddings, disable=not show_progress, desc="ST scoring"):
                    # Compute cosine similarity with all SDG embeddings
                    similarities = np.dot(self._sdg_embeddings_matrix, emb) / (
                        np.linalg.norm(self._sdg_embeddings_matrix, axis=1) * np.linalg.norm(emb) + 1e-8
                    )
                    sdg_scores = {}
                    for sdg_num in range(1, 18):
                        threshold = self.get_threshold(sdg_num)
                        sdg_scores[sdg_num] = {
                            "score": float(similarities[sdg_num - 1]),
                            "is_aligned": similarities[sdg_num - 1] >= threshold,
                            "sdg_name": self.sdg_reference.get_sdg_name(sdg_num),
                            "threshold_used": threshold
                        }
                    # Get top SDG
                    top_sdg = max(sdg_scores.keys(), key=lambda k: sdg_scores[k]["score"])
                    all_st_scores.append({
                        "sdg_scores": sdg_scores,
                        "top_sdg": top_sdg,
                        "top_score": sdg_scores[top_sdg]["score"]
                    })

                # BATCH: Get sdgBERT predictions
                if show_progress:
                    print(f"  Computing sdgBERT predictions...")
                sdg_bert_results = self.sdg_bert.predict_batch(texts, batch_size=batch_size, show_progress=show_progress)

                # Combine results
                if show_progress:
                    print(f"  Combining scores...")
                iterator = tqdm(range(len(valid_activities)), disable=not show_progress, desc="Combining")
                for i in iterator:
                    activity = valid_activities[i]
                    st_result = all_st_scores[i]
                    sdg_bert_pred = sdg_bert_results[i]

                    # Combine using ensemble
                    combined_scores = self._combine_scores(st_result["sdg_scores"], sdg_bert_pred)

                    # Apply SDG 17 bias correction if enabled
                    if self.enable_sdg17_correction:
                        combined_scores = apply_sdg17_corrections(
                            texts[i],
                            combined_scores,
                            correction_method=self.sdg17_correction_method
                        )

                    # Apply SDG 11 bias correction if enabled
                    if self.enable_sdg11_correction:
                        combined_scores = apply_sdg11_corrections(
                            texts[i],
                            combined_scores,
                            activity_metadata=None,
                            correction_method=self.sdg11_correction_method
                        )

                    # Apply SDG 14 bias correction if enabled
                    if self.enable_sdg14_correction:
                        combined_scores = apply_sdg14_corrections(
                            texts[i],
                            combined_scores,
                            activity_metadata=None,
                            correction_method=self.sdg14_correction_method
                        )

                    # Apply SDG 4 bias correction if enabled
                    if self.enable_sdg4_correction:
                        combined_scores = apply_sdg4_corrections(
                            texts[i],
                            combined_scores,
                            correction_method=self.sdg4_correction_method
                        )

                    # Apply SDG 6 bias correction if enabled
                    if self.enable_sdg6_correction:
                        combined_scores = apply_sdg6_corrections(
                            texts[i],
                            combined_scores,
                            correction_method=self.sdg6_correction_method
                        )

                    # Apply SDG 8 bias correction if enabled
                    if self.enable_sdg8_correction:
                        combined_scores = apply_sdg8_corrections(
                            texts[i],
                            combined_scores,
                            correction_method=self.sdg8_correction_method
                        )

                    # Apply SDG 10 bias correction if enabled
                    if self.enable_sdg10_correction:
                        combined_scores = apply_sdg10_corrections(
                            texts[i],
                            combined_scores,
                            correction_method=self.sdg10_correction_method
                        )

                    # Apply SDG 12 bias correction if enabled
                    if self.enable_sdg12_correction:
                        combined_scores = apply_sdg12_corrections(
                            texts[i],
                            combined_scores,
                            correction_method=self.sdg12_correction_method
                        )

                    # Apply SDG 16 bias correction if enabled
                    if self.enable_sdg16_correction:
                        combined_scores = apply_sdg16_corrections(
                            texts[i],
                            combined_scores,
                            correction_method=self.sdg16_correction_method
                        )

                    # Find top SDG
                    top_sdg = max(combined_scores.keys(), key=lambda k: combined_scores[k]["score"])

                    alignment = {
                        "activity_text": texts[i],
                        "word_count": len(texts[i].split()),
                        "sdg_scores": combined_scores,
                        "top_sdg": top_sdg,
                        "top_sdg_name": combined_scores[top_sdg]["sdg_name"],
                        "top_score": combined_scores[top_sdg]["score"],
                        "num_aligned": sum(1 for s in combined_scores.values() if s["is_aligned"]),
                        "ensemble_info": {
                            "st_top_sdg": st_result["top_sdg"],
                            "st_score": st_result["top_score"],
                            "sdg_bert_prediction": sdg_bert_pred["sdg"],
                            "sdg_bert_confidence": sdg_bert_pred["confidence"]
                        }
                    }

                    result = {**activity, **alignment}
                    results.append(result)

                return results

            except Exception as e:
                logger.error(f"sdgBERT batch prediction failed: {e}", exc_info=True)
                warnings.warn(f"sdgBERT batch prediction failed: {e}. Falling back to individual processing.")

        # Fallback to individual processing
        logger.info(f"Falling back to individual processing for {len(valid_activities)} activities")
        results = []
        iterator = tqdm(valid_activities, desc="Aligning activities", disable=not show_progress) if show_progress else valid_activities

        for activity in iterator:
            text = activity.get("text", "")
            alignment = self.align_activity(text, use_ensemble=use_ensemble)
            result = {**activity, **alignment}
            results.append(result)

        logger.info(f"Individual processing complete: {len(results)} activities aligned")
        return results

    def align_report(
        self,
        activities_data: Dict[str, Any],
        show_progress: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Process a full report and compute SDG alignment using hybrid approach.

        Args:
            activities_data: Output from ActivityExtractor
            show_progress: Whether to show progress bar
            use_cache: Whether to use cached embeddings

        Returns:
            Dictionary with alignment results including hybrid threshold config
        """
        import time
        start_time = time.time()

        # Get activities from data
        activities = activities_data.get("activities", [])
        logger.info(f"Starting report alignment: {len(activities)} activities from {activities_data.get('source', 'unknown')}")

        # Align activities using hybrid approach
        aligned_activities = self.align_activities(
            activities,
            show_progress=show_progress,
            use_ensemble=True,
            batch_size=32
        )

        # Compute report-level statistics
        report_alignment = self.compute_report_alignment(aligned_activities)

        # Get all SDG-specific thresholds for hybrid mode
        all_thresholds = self.config.get_all_similarity_thresholds('hybrid')

        elapsed = time.time() - start_time
        logger.info(f"Report alignment complete in {elapsed:.2f}s: {report_alignment['total_activities']} activities, {len(report_alignment['top_sdgs'])} SDGs covered")

        return {
            "source": activities_data.get("source", ""),
            "metadata": activities_data.get("metadata", {}),
            "alignment_config": {
                "model": self.model_name,
                "similarity_threshold": self.similarity_threshold,
                "threshold_mode": "sdg_specific",
                "threshold_source": "hybrid",
                "sdg_specific_thresholds": all_thresholds,
                "ensemble_mode": self.ensemble_mode,
                "sdg_bert_weight": self.sdg_bert_weight,
                "st_weight": self.st_weight
            },
            "activities": aligned_activities,
            "report_alignment": report_alignment
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        info = {
            "sentence_transformer": {
                "model_name": self.model_name,
                "similarity_threshold": self.similarity_threshold,
                "accuracy": 0.876  # From evaluation
            },
            "sdg_bert": None,
            "ensemble_mode": self.ensemble_mode,
            "ensemble_weights": {
                "sdg_bert": self.sdg_bert_weight,
                "sentence_transformer": self.st_weight
            },
            "sdg_specific_weights": True,  # Now using SDG-specific weights
            "sdg_weights_source": "src.sdg_ensemble_weights",
            "sdg_bert_load_status": "loaded" if self.sdg_bert else ("failed" if self._sdg_bert_load_error else "not_requested")
        }

        if self.sdg_bert:
            info["sdg_bert"] = self.sdg_bert.get_model_info()
        elif self._sdg_bert_load_error:
            info["sdg_bert_load_error"] = self._sdg_bert_load_error

        return info
    
    def compare_models(
        self,
        texts: List[str],
        true_labels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Compare sentence transformer and sdgBERT on sample texts.

        Args:
            texts: List of texts to classify
            true_labels: Optional true labels for accuracy calculation

        Returns:
            Comparison statistics
        """
        if not self.sdg_bert:
            if self._sdg_bert_load_error:
                raise ModelLoadError(f"sdgBERT failed to load: {self._sdg_bert_load_error}")
            raise ModelLoadError("sdgBERT not loaded. Initialize with use_sdg_bert=True")

        from src.sdg_bert_classifier import compare_classifiers

        return compare_classifiers(texts, self, self.sdg_bert, true_labels)


def create_alignment_engine(
    model_name: Optional[str] = None,
    similarity_threshold: Optional[float] = None,
    use_hybrid: bool = False,
    **hybrid_kwargs
) -> AlignmentEngine:
    """
    Factory function to create alignment engine.
    
    Args:
        model_name: Sentence transformer model name
        similarity_threshold: Similarity threshold
        use_hybrid: Whether to use HybridAlignmentEngine with sdgBERT support
        **hybrid_kwargs: Additional arguments for HybridAlignmentEngine
        
    Returns:
        AlignmentEngine or HybridAlignmentEngine instance
    """
    if use_hybrid:
        return HybridAlignmentEngine(
            model_name=model_name,
            similarity_threshold=similarity_threshold,
            **hybrid_kwargs
        )
    else:
        return AlignmentEngine(
            model_name=model_name,
            similarity_threshold=similarity_threshold
        )
