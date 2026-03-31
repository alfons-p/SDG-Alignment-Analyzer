"""SDG 10 Bias Correction Module.

Implements post-processing corrections for SDG 10 (Reduced Inequalities)
misclassification issues.

Root Cause:
- Financial activities (liquidity, depreciation) being classified as inequality
- Generic "inequality" keywords in financial context
- Asset management triggering inequality keywords

Correction Approach:
- Exclude financial/accounting activities from SDG 10
- Require social context for inequality classification
- Boost SDG 16 for financial governance activities
"""

from typing import Dict, Any, List, Tuple

# Keywords that indicate TRUE inequality focus (SDG 10)
SDG10_INEQUALITY_KEYWORDS = [
    "inequality", "disability", "inclusion", "diversity", "accessible",
    "marginalized", "vulnerable", "disadvantaged", "social inclusion",
    "equal opportunity", "discrimination", "minority", "refugee",
    "people with disability", "access for all", "inclusive",
    "disability inclusion action plan", "diap", "accessibility plan"
]

# Activities that should NOT be classified as SDG 10
SDG10_EXCLUSION_PATTERNS = [
    # Financial activities (should be SDG 16 or no SDG)
    "liquidity", "depreciation", "asset value", "fair value",
    "financial liability", "carrying amount", "impairment",
    "cost index", "valuation", "benchmark", "financial statements",
    # Governance (should be SDG 16)
    "benchmark", "target", "ratio", "percentage",
    # Cultural heritage (should be SDG 11.4)
    "heritage", "cultural heritage", "history", "historical",
    "historical society", "museum", "archives", "cultural event",
    "history & heritage", "indigenous", "reconciliation"
]

# Penalty for SDG 10 when exclusion patterns found
SDG10_PENALTY = 0.40


def contains_inequality_keywords(text: str) -> bool:
    """Check if text contains true inequality keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in SDG10_INEQUALITY_KEYWORDS)


def contains_exclusion_patterns(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains patterns that should NOT trigger SDG 10."""
    text_lower = text.lower()
    found = []
    for pattern in SDG10_EXCLUSION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern)
    return len(found) > 0, found


def apply_sdg10_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 10 bias corrections to alignment scores.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        correction_method: Which correction to apply

    Returns:
        Updated SDG scores with corrections applied
    """
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 10 not in scores:
        return scores

    text_lower = activity_text.lower()
    original_score = scores[10]['score']

    # Check for true inequality keywords
    has_inequality = contains_inequality_keywords(activity_text)

    # Check for exclusion patterns
    has_exclusion, found_exclusions = contains_exclusion_patterns(activity_text)

    # Apply corrections
    if correction_method in ("penalty", "all"):
        if has_exclusion and not has_inequality:
            # Penalize SDG 10 for financial activities
            scores[10]['score'] = max(0.0, original_score - SDG10_PENALTY)
            scores[10]['correction_applied'] = True

    # Boost SDG 16 for financial governance
    if correction_method in ("reassign", "all"):
        if has_exclusion:
            if 16 in scores:
                scores[16]['score'] = min(1.0, scores[16]['score'] + 0.15)

    return scores


def create_sdg10_corrector(method: str = "all", enabled: bool = True) -> callable:
    """Create an SDG 10 corrector function."""
    def corrector(
        activity_text: str,
        sdg_scores: Dict[int, Dict[str, Any]],
        activity_metadata: Dict[str, Any] = None
    ) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg10_corrections(activity_text, sdg_scores, method)
    return corrector