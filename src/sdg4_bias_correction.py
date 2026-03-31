"""SDG 4 Bias Correction Module.

Implements post-processing corrections for SDG 4 (Quality Education)
misclassification issues.

Root Cause:
- Arts and cultural activities being classified as education
- Sports personality descriptions triggering education keywords
- Generic "learning" and "training" without educational context

Correction Approach:
- Exclude arts/entertainment/cultural activities from SDG 4
- Require educational context for classification
- Boost alternative SDGs for arts/cultural activities
"""

from typing import Dict, Any, List, Tuple

# Keywords that indicate TRUE education (SDG 4)
SDG4_EDUCATION_KEYWORDS = [
    "school", "education", "learning", "teaching", "curriculum",
    "student", "teacher", "classroom", "kindergarten", "preschool",
    "university", "college", "training program", "vocational",
    "literacy", "scholarship", "enrollment", "graduation"
]

# Activities that should NOT be classified as SDG 4
SDG4_EXCLUSION_PATTERNS = [
    # Arts and entertainment (should be SDG 11 community or no SDG)
    "arts", "art gallery", "cultural event", "museum", "exhibition",
    "performance", "concert", "festival", "theatre", "theater",
    # Sports and recreation (should be SDG 3 health)
    "sports", "rugby", "football", "cricket", "athletics", "player",
    "former player", "representative", "league", "game", "match",
    "soccer", "sporting", "recreation club",
    # Community engagement (should be SDG 11)
    "youth week", "youth engagement", "migrant community", "community support",
    "community group", "community program",
    # Parent support (should be SDG 3 or SDG 16)
    "parent support", "parenting", "family support group",
    # Council governance (should be SDG 16)
    "councillor", "council meeting", "governance", "committee chair",
    "advocacy", "policy", "advocate",
    # Infrastructure and construction (should be SDG 9 or 11)
    "playground", "construction", "infrastructure project", "facility upgrade",
    "capital works", "building project", "asset management",
    # Environmental programs (should be SDG 13 or 15)
    "wildflower garden", "environmental education", "nature program",
    "biodiversity", "conservation program",
]

# SDG reassignment for excluded activities
SDG4_REASSIGNMENT = {
    "arts": 11,  # Community/cultural activities
    "sports": 3,  # Health and well-being
    "councillor": 16,  # Governance
    "committee": 16,  # Governance
    "advocacy": 16,  # Governance
}

# Penalty for SDG 4 when exclusion patterns found
SDG4_PENALTY = 0.35


def contains_education_keywords(text: str) -> bool:
    """Check if text contains true education keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in SDG4_EDUCATION_KEYWORDS)


def contains_exclusion_patterns(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains patterns that should NOT trigger SDG 4."""
    text_lower = text.lower()
    found = []
    for pattern in SDG4_EXCLUSION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern)
    return len(found) > 0, found


def apply_sdg4_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 4 bias corrections to alignment scores.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        correction_method: Which correction to apply

    Returns:
        Updated SDG scores with corrections applied
    """
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 4 not in scores:
        return scores

    text_lower = activity_text.lower()
    original_score = scores[4]['score']

    # Check for true education keywords
    has_education = contains_education_keywords(activity_text)

    # Check for exclusion patterns
    has_exclusion, found_exclusions = contains_exclusion_patterns(activity_text)

    # Apply corrections
    if correction_method in ("penalty", "all"):
        if has_exclusion and not has_education:
            # Penalize SDG 4 for arts/sports/governance activities
            scores[4]['score'] = max(0.0, original_score - SDG4_PENALTY)
            scores[4]['correction_applied'] = True

    # Re-assign to correct SDG
    if correction_method in ("reassign", "all"):
        for pattern, target_sdg in SDG4_REASSIGNMENT.items():
            if pattern in text_lower:
                if target_sdg in scores:
                    scores[target_sdg]['score'] = min(1.0, scores[target_sdg]['score'] + 0.15)

    return scores


def create_sdg4_corrector(method: str = "all", enabled: bool = True) -> callable:
    """Create an SDG 4 corrector function."""
    def corrector(
        activity_text: str,
        sdg_scores: Dict[int, Dict[str, Any]],
        activity_metadata: Dict[str, Any] = None
    ) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg4_corrections(activity_text, sdg_scores, method)
    return corrector