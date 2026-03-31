"""Context-Aware SDG Alignment Engine.

Enhances SDG alignment scoring by considering document context (section type)
and applying relevance weighting based on section-SDG mappings.
"""

from typing import Dict, List, Any, Optional
import numpy as np
from src.alignment_engine import AlignmentEngine


class ContextAwareAlignmentEngine(AlignmentEngine):
    """
    SDG Alignment Engine with context-aware scoring.

    Enhances base alignment by:
    1. Identifying document section context (environment, community, economic, etc.)
    2. Applying section-specific SDG relevance weights
    3. Boosting scores for SDGs relevant to the section
    4. Providing context confidence scores
    """

    # Mapping of section types to relevant SDG categories
    # Weights: 1.0 = neutral, 1.2 = relevant, 1.5 = highly relevant, 0.8 = less relevant
    SECTION_SDG_WEIGHTS = {
        "environment": {
            6: 1.5,   # Clean Water and Sanitation
            7: 1.5,   # Affordable and Clean Energy
            11: 1.3,  # Sustainable Cities
            12: 1.5,  # Responsible Consumption
            13: 1.5,  # Climate Action
            14: 1.4,  # Life Below Water
            15: 1.4,  # Life on Land
        },
        "community": {
            1: 1.2,   # No Poverty
            2: 1.2,   # Zero Hunger
            3: 1.4,   # Good Health
            4: 1.4,   # Quality Education
            5: 1.3,   # Gender Equality
            10: 1.4,  # Reduced Inequalities
            11: 1.3,  # Sustainable Cities
            16: 1.3,  # Peace and Justice
            17: 1.2,  # Partnerships
        },
        "economic": {
            1: 1.2,   # No Poverty
            8: 1.5,   # Decent Work
            9: 1.4,   # Industry and Innovation
            10: 1.2,  # Reduced Inequalities
            12: 1.2,  # Responsible Consumption
            17: 1.3,  # Partnerships
        },
        "infrastructure": {
            6: 1.3,   # Clean Water
            7: 1.4,   # Clean Energy
            9: 1.5,   # Industry and Innovation
            11: 1.5,  # Sustainable Cities (strong match)
        },
        "planning": {
            9: 1.3,   # Industry and Innovation
            11: 1.5,  # Sustainable Cities (strong match)
            15: 1.2,  # Life on Land (urban planning)
        },
        "governance": {
            10: 1.3,  # Reduced Inequalities
            11: 1.2,  # Sustainable Cities
            16: 1.5,  # Peace, Justice and Strong Institutions
            17: 1.4,  # Partnerships
        },
        "finance": {
            1: 1.3,   # No Poverty
            8: 1.3,   # Decent Work
            10: 1.2,  # Reduced Inequalities
            17: 1.3,  # Partnerships
        },
    }

    def __init__(
        self,
        model_name: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        context_weight: float = 0.3,
        min_context_score: float = 0.2
    ):
        """
        Initialize context-aware alignment engine.

        Args:
            model_name: Sentence transformer model name
            similarity_threshold: Minimum similarity for alignment
            context_weight: How much to weight context (0-1, higher = more context influence)
            min_context_score: Minimum score to consider context valid
        """
        super().__init__(model_name, similarity_threshold)
        self.context_weight = context_weight
        self.min_context_score = min_context_score

    def align_activity(
        self,
        activity_text: str,
        section_type: Optional[str] = None,
        return_top_n: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Align a single activity with context awareness.

        Args:
            activity_text: Activity description
            section_type: Document section type (environment, community, economic, etc.)
            return_top_n: Return only top N SDGs

        Returns:
            Dictionary with scores and context information
        """
        # Get base alignment from parent class
        result = super().align_activity(activity_text, return_top_n=None)

        # Apply context weighting if section type is provided
        if section_type and section_type.lower() in self.SECTION_SDG_WEIGHTS:
            result = self._apply_context_weights(
                result,
                section_type.lower()
            )

        # Sort SDGs by (potentially updated) scores
        scores = result["sdg_scores"]
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        # Update top SDG
        if sorted_scores:
            top_sdg = sorted_scores[0][0]
            result["top_sdg"] = top_sdg
            result["top_sdg_name"] = scores[top_sdg]["sdg_name"]
            result["top_score"] = scores[top_sdg]["score"]

        # Re-count aligned SDGs with new scores
        # Use SDG-specific threshold from threshold_config.py
        result["num_aligned"] = sum(
            1 for sdg_num, s in scores.items()
            if s["score"] >= self.get_threshold_for_sdg(sdg_num)
        )

        # Add context information
        if section_type:
            result["context"] = {
                "section_type": section_type,
                "context_weight": self.context_weight,
                "section_relevant_sdgs": list(
                    self.SECTION_SDG_WEIGHTS.get(section_type.lower(), {}).keys()
                )
            }

        # Return only top N if requested
        if return_top_n:
            result["top_sdgs"] = [
                {"sdg": sdg, "name": data["sdg_name"], "score": data["score"]}
                for sdg, data in sorted_scores[:return_top_n]
            ]

        return result

    def _apply_context_weights(
        self,
        result: Dict[str, Any],
        section_type: str
    ) -> Dict[str, Any]:
        """
        Apply section-specific weights to SDG scores.

        Args:
            result: Alignment result from base engine
            section_type: Document section type

        Returns:
            Updated result with weighted scores
        """
        section_weights = self.SECTION_SDG_WEIGHTS.get(section_type, {})

        if not section_weights:
            return result

        scores = result["sdg_scores"]

        # Calculate weighted scores
        for sdg_num, sdg_data in scores.items():
            base_score = sdg_data["score"]
            weight = section_weights.get(sdg_num, 1.0)

            # Apply weighted boost
            # Formula: weighted_score = base_score * (1 + weight_adjustment)
            # where adjustment is proportional to context_weight
            weight_adjustment = (weight - 1.0) * self.context_weight
            weighted_score = base_score * (1 + weight_adjustment)

            # Cap at 1.0
            weighted_score = min(weighted_score, 1.0)

            # Update score and alignment status
            sdg_data["score"] = round(weighted_score, 4)
            # Use SDG-specific threshold from threshold_config.py
            sdg_data["is_aligned"] = weighted_score >= self.get_threshold_for_sdg(sdg_num)
            sdg_data["base_score"] = round(base_score, 4)  # Keep original
            sdg_data["context_weight"] = weight

        return result

    def align_activities(
        self,
        activities: List[Dict[str, Any]],
        show_progress: bool = True,
        batch_size: int = 32
    ) -> List[Dict[str, Any]]:
        """
        Align multiple activities with context awareness.

        Args:
            activities: List of activity dictionaries with 'text' and optionally 'section_type'
            show_progress: Whether to show progress bar
            batch_size: Batch size for encoding

        Returns:
            List of activity alignment results with context
        """
        results = []

        # Process each activity with its context
        iterator = activities if not show_progress else tqdm(activities, desc="Aligning activities")

        for activity in iterator:
            text = activity.get("text", "")
            section_type = activity.get("section_type")

            if text:
                result = self.align_activity(text, section_type=section_type)
                results.append(result)

        return results

    def get_section_sdg_relevance(self, section_type: str) -> Dict[int, float]:
        """
        Get the SDG relevance weights for a section type.

        Args:
            section_type: Document section type

        Returns:
            Dictionary mapping SDG numbers to relevance weights
        """
        return self.SECTION_SDG_WEIGHTS.get(section_type.lower(), {})

    def explain_context_boost(
        self,
        activity_text: str,
        section_type: str,
        sdg_num: int
    ) -> Dict[str, Any]:
        """
        Explain how context affected the score for a specific SDG.

        Args:
            activity_text: Activity description
            section_type: Document section type
            sdg_num: SDG number to explain

        Returns:
            Explanation dictionary with base score, weight, and final score
        """
        # Get alignment without context
        result_no_context = super().align_activity(activity_text, return_top_n=None)
        base_score = result_no_context["sdg_scores"][sdg_num]["score"]

        # Get alignment with context
        result_with_context = self.align_activity(
            activity_text,
            section_type=section_type,
            return_top_n=None
        )
        final_score = result_with_context["sdg_scores"][sdg_num]["score"]
        weight = result_with_context["sdg_scores"][sdg_num].get("context_weight", 1.0)

        return {
            "activity_text": activity_text,
            "section_type": section_type,
            "sdg": sdg_num,
            "sdg_name": result_with_context["sdg_scores"][sdg_num]["sdg_name"],
            "base_score": round(base_score, 4),
            "context_weight": weight,
            "context_weight_applied": self.context_weight,
            "final_score": round(final_score, 4),
            "boost_percentage": round(((final_score - base_score) / base_score * 100), 2) if base_score > 0 else 0
        }
