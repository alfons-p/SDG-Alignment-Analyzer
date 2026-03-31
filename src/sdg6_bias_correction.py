"""SDG 6 Bias Correction Module.

Implements post-processing corrections for SDG 6 (Clean Water and Sanitation)
misclassification issues.

Root Cause:
- Infrastructure activities (culverts, drains, stormwater) being classified as SDG 6
- "Water" in project names triggering clean water classification
- Stormwater infrastructure being confused with water supply

Correction Approach:
- Exclude infrastructure/ drainage activities from SDG 6
- Require explicit water supply/sanitation context for classification
- Re-assign infrastructure activities to SDG 9 or 11
"""

from typing import Dict, Any, List, Tuple

# Keywords that indicate TRUE SDG 6 (Clean Water and Sanitation)
SDG6_WATER_KEYWORDS = [
    "drinking water", "water supply", "water quality", "sanitation",
    "wastewater treatment", "sewage", "sewer", "water treatment",
    "water infrastructure", "water service", "potable water",
    "water management", "water resource", "dam", "reservoir",
    "groundwater", "surface water", "water conservation",
    "rainwater harvesting", "water recycling", "grey water"
]

# Activities that should NOT be classified as SDG 6
SDG6_EXCLUSION_PATTERNS = [
    # Infrastructure activities (should be SDG 9 or 11)
    "culvert", "constructed culvert", "drainage infrastructure",
    "stormwater drain", "stormwater drainag", "drainage upgrade",
    "road drainage", "drainage system", "drainage works",
    # Construction without water context
    "construction of", "construction project", "civil works",
    "road works", "bridge construction", "footpath construction",
    # Generic infrastructure
    "infrastructure upgrade", "infrastructure works", "asset renewal"
]

# Penalty for SDG 6 when exclusion patterns found
SDG6_PENALTY = 0.45


def contains_water_keywords(text: str) -> bool:
    """Check if text contains true water/sanitation keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in SDG6_WATER_KEYWORDS)


def contains_exclusion_patterns(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains patterns that should NOT trigger SDG 6."""
    text_lower = text.lower()
    found = []
    for pattern in SDG6_EXCLUSION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern)
    return len(found) > 0, found


def apply_sdg6_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 6 bias corrections to alignment scores.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        correction_method: Which correction to apply

    Returns:
        Updated SDG scores with corrections applied
    """
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 6 not in scores:
        return scores

    text_lower = activity_text.lower()
    original_score = scores[6]['score']

    # Check for true water keywords
    has_water = contains_water_keywords(activity_text)

    # Check for exclusion patterns
    has_exclusion, found_exclusions = contains_exclusion_patterns(activity_text)

    # Apply corrections
    if correction_method in ("penalty", "all"):
        if has_exclusion and not has_water:
            # Penalize SDG 6 for infrastructure activities
            scores[6]['score'] = max(0.0, original_score - SDG6_PENALTY)
            scores[6]['correction_applied'] = True

    # Re-assign to infrastructure SDGs
    if correction_method in ("reassign", "all"):
        if has_exclusion:
            # Check for infrastructure keywords and boost SDG 9 or 11
            infrastructure_keywords = ["culvert", "drainage", "stormwater",
                                      "road", "bridge", "footpath", "infrastructure"]
            has_infrastructure = any(kw in text_lower for kw in infrastructure_keywords)
            if has_infrastructure:
                # Boost SDG 11 (Sustainable Cities) for infrastructure
                if 11 in scores:
                    scores[11]['score'] = min(1.0, scores[11]['score'] + 0.10)

    return scores


def create_sdg6_corrector(method: str = "all", enabled: bool = True) -> callable:
    """Create an SDG 6 corrector function."""
    def corrector(
        activity_text: str,
        sdg_scores: Dict[int, Dict[str, Any]],
        activity_metadata: Dict[str, Any] = None
    ) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg6_corrections(activity_text, sdg_scores, method)
    return corrector