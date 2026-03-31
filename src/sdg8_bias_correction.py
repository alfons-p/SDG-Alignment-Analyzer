"""SDG 8 Bias Correction Module.

Implements post-processing corrections for SDG 8 (Decent Work and Economic Growth)
misclassification issues.

Root Cause:
- Financial activities being classified as economic growth
- "Deliver", "deliver", "actions" triggering economic keywords
- Staff/organizational activities triggering employment keywords

Correction Approach:
- Exclude financial/governance activities from SDG 8
- Require employment/business context for classification
- Boost SDG 16 for governance activities
"""

from typing import Dict, Any, List, Tuple

# Keywords that indicate TRUE economic growth (SDG 8)
SDG8_ECONOMIC_KEYWORDS = [
    "employment", "jobs", "workforce", "economic development",
    "tourism", "business support", "industry", "trade",
    "local economy", "job creation", "skills development",
    "workplace", "training program", "employment services"
]

# Activities that should NOT be classified as SDG 8
SDG8_EXCLUSION_PATTERNS = [
    # Financial activities (should be SDG 16 or no SDG)
    "financial statement", "audit fees", "depreciation",
    "financial liability", "carrying amount", "impairment",
    "valuation", "fair value", "cost index",
    "commissions", "licencing", "ticket sales", "revenue",
    "grants program", "event grants", "funding to community",
    "going concern", "financial report", "financial position",
    "financial sustainability", "controlled revenue",
    "revenue ratio", "annual report",
    # Governance (should be SDG 16)
    "internal control", "governance", "councillor", "council",
    "deliver actions", "action plan", "strategic plan",
    "annual report", "business plan", "corporate",
    "strategic framework", "delivery program",
    # WHS and workplace safety (should be SDG 16 or no SDG)
    "workplace health and safety", "whs obligations", "safety management",
    "workplace safety", "safety obligations", "staff recruitment",
    # Administrative (no SDG)
    "staff housing", "people culture", "systems",
    "reserve fund", "housing reserve",
    # Education and training (should be SDG 4)
    "learning and participation", "library branches", "library services",
    "educational institution", "student placement", "kindergarten",
    "early learning", "early childhood education",
    # Social enterprise partnerships (should be SDG 17 or SDG 4)
    "social enterprise", "community partnership", "partner with social",
    # Skills development in education context (should be SDG 4)
    "skills development and training", "training opportunities",
    "vocational training", "workforce development program"
]

# Penalty for SDG 8 when exclusion patterns found
SDG8_PENALTY = 0.40


def contains_economic_keywords(text: str) -> bool:
    """Check if text contains true economic keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in SDG8_ECONOMIC_KEYWORDS)


def contains_exclusion_patterns(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains patterns that should NOT trigger SDG 8."""
    text_lower = text.lower()
    found = []
    for pattern in SDG8_EXCLUSION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern)
    return len(found) > 0, found


def apply_sdg8_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 8 bias corrections to alignment scores.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        correction_method: Which correction to apply

    Returns:
        Updated SDG scores with corrections applied
    """
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 8 not in scores:
        return scores

    text_lower = activity_text.lower()
    original_score = scores[8]['score']

    # Check for true economic keywords
    has_economic = contains_economic_keywords(activity_text)

    # Check for exclusion patterns
    has_exclusion, found_exclusions = contains_exclusion_patterns(activity_text)

    # Apply corrections
    if correction_method in ("penalty", "all"):
        if has_exclusion and not has_economic:
            # Penalize SDG 8 for financial/governance activities
            scores[8]['score'] = max(0.0, original_score - SDG8_PENALTY)
            scores[8]['correction_applied'] = True

    # Boost SDG 16 for governance
    if correction_method in ("reassign", "all"):
        if has_exclusion:
            if 16 in scores:
                scores[16]['score'] = min(1.0, scores[16]['score'] + 0.15)

    return scores


def create_sdg8_corrector(method: str = "all", enabled: bool = True) -> callable:
    """Create an SDG 8 corrector function."""
    def corrector(
        activity_text: str,
        sdg_scores: Dict[int, Dict[str, Any]],
        activity_metadata: Dict[str, Any] = None
    ) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg8_corrections(activity_text, sdg_scores, method)
    return corrector