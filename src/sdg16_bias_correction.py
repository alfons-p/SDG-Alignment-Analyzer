"""SDG 16 Bias Correction Module.

Implements post-processing corrections for SDG 16 (Peace, Justice and Strong Institutions)
misclassification issues.

Root Cause:
- Infrastructure activities being classified as governance
- Financial reporting triggering governance keywords
- Procurement activities triggering institution keywords

Correction Approach:
- Exclude infrastructure and asset management activities from SDG 16
- Penalize weak governance matches (financial reports without governance context)
- Boost true governance keywords
"""

from typing import Dict, Any, List, Tuple

# Keywords that indicate TRUE SDG 16 (governance, justice, institutions)
SDG16_GOVERNANCE_KEYWORDS = [
    "governance", "transparency", "accountability", "audit committee",
    "risk management", "internal audit", "code of conduct", "ethics",
    "anti-corruption", "disclosure", "compliance", "regulatory",
    "councillor", "elected member", "council meeting", "council resolution",
    "public participation", "community engagement", "stakeholder",
    "policy development", "strategic planning", "business continuity",
    "fraud prevention", "whistleblower", "conflict of interest"
]

# Activities that should NOT be classified as SDG 16
SDG16_EXCLUSION_PATTERNS = [
    # Infrastructure and asset management (should be SDG 9 or 11)
    "condition survey", "road survey", "footpath survey",
    "infrastructure condition", "asset condition", "asset management",
    "road maintenance", "footpath maintenance", "bridge maintenance",
    "infrastructure inspection", "asset inspection",
    # Procurement (should be SDG 12 or no SDG)
    "procurement dashboard", "procurement activity", "tender activity",
    "procurement process", "purchasing", "supply chain",
    # Financial reporting without governance context (weak SDG 16)
    "market approach", "fair value measurement", "valuation method",
    "financial indicator", "financial metrics", "ratio analysis",
    "carrying amount", "impairment test", "depreciation",
    # General administrative (no SDG)
    "administrative support", "general administration",
    "office management", "clerical"
]

# Penalty for SDG 16 when exclusion patterns found
SDG16_PENALTY = 0.40

# Bonus for SDG 16 when true governance keywords found
SDG16_BONUS = 0.15


def contains_governance_keywords(text: str) -> bool:
    """Check if text contains true governance keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in SDG16_GOVERNANCE_KEYWORDS)


def contains_exclusion_patterns(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains patterns that should NOT trigger SDG 16."""
    text_lower = text.lower()
    found = []
    for pattern in SDG16_EXCLUSION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern)
    return len(found) > 0, found


def apply_sdg16_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 16 bias corrections to alignment scores.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        correction_method: Which correction to apply

    Returns:
        Updated SDG scores with corrections applied
    """
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 16 not in scores:
        return scores

    text_lower = activity_text.lower()
    original_score = scores[16]['score']

    # Check for true governance keywords
    has_governance = contains_governance_keywords(activity_text)

    # Check for exclusion patterns
    has_exclusion, found_exclusions = contains_exclusion_patterns(activity_text)

    # Apply corrections
    if correction_method in ("penalty", "all"):
        if has_exclusion and not has_governance:
            # Penalize SDG 16 for infrastructure/procurement activities
            scores[16]['score'] = max(0.0, original_score - SDG16_PENALTY)
            scores[16]['correction_applied'] = True

    # Boost for true governance content
    if correction_method in ("bonus", "all"):
        if has_governance and not has_exclusion:
            scores[16]['score'] = min(1.0, original_score + SDG16_BONUS)

    # Re-assign infrastructure activities to SDG 9 or 11
    if correction_method in ("reassign", "all"):
        if has_exclusion:
            # Check for infrastructure keywords and boost SDG 9 or 11
            infrastructure_keywords = ["road", "footpath", "bridge", "infrastructure",
                                      "asset", "facility", "building"]
            has_infrastructure = any(kw in text_lower for kw in infrastructure_keywords)
            if has_infrastructure and 11 in scores:
                scores[11]['score'] = min(1.0, scores[11]['score'] + 0.10)

            # Check for procurement and boost SDG 12
            procurement_keywords = ["procurement", "tender", "purchasing", "supply"]
            has_procurement = any(kw in text_lower for kw in procurement_keywords)
            if has_procurement and 12 in scores:
                scores[12]['score'] = min(1.0, scores[12]['score'] + 0.10)

    return scores


def create_sdg16_corrector(method: str = "all", enabled: bool = True) -> callable:
    """Create an SDG 16 corrector function."""
    def corrector(
        activity_text: str,
        sdg_scores: Dict[int, Dict[str, Any]],
        activity_metadata: Dict[str, Any] = None
    ) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg16_corrections(activity_text, sdg_scores, method)
    return corrector