"""SDG 12 Bias Correction Module.

Implements post-processing corrections for SDG 12 (Responsible Consumption and Production)
misclassification issues.

Root Cause:
- Financial valuation activities being classified as consumption
- "Fair value" and "cost index" triggering sustainability keywords
- Asset management triggering waste keywords

Correction Approach:
- Exclude financial/accounting activities from SDG 12
- Require waste/sustainability context for classification
- Boost SDG 16 for financial governance activities
"""

from typing import Dict, Any, List, Tuple

# Keywords that indicate TRUE sustainable consumption (SDG 12)
# Must be explicit waste/recycling/sustainability context
SDG12_SUSTAINABILITY_KEYWORDS = [
    "waste", "recycling", "recycle", "sustainable consumption",
    "circular economy", "waste management", "composting", "landfill",
    "reuse", "reduce", "waste reduction", "waste diversion",
    "green procurement", "sustainable production", "zero waste",
    "waste collection", "waste disposal", "recyclable"
]

# Activities that should NOT be classified as SDG 12
SDG12_EXCLUSION_PATTERNS = [
    # Financial activities (should be SDG 16 or no SDG)
    "fair value", "depreciation", "valuation", "asset value",
    "cost index", "carrying amount", "impairment", "revaluation",
    "financial statements", "accounting", "audit", "balance sheet",
    "inventories", "receivables", "capitalised", "amortisation",
    "financial report", "financial position", "cash flow",
    # Audit and assurance activities (should be SDG 16 or no SDG)
    "auditors' report", "auditor's report", "internal audit",
    "quality assurance", "kpi monitoring", "monitoring of agreed kpis",
    "audit committee", "external audit", "audit report",
    "authorised for issue", "independent accounting",
    # Governance (should be SDG 16)
    "benchmark", "ratio", "percentage", "measurement",
    "service delivery", "management services", "annual report",
    # General administrative (no SDG)
    "business plan", "corporate", "strategic plan",
    # General sustainability without waste context (should be SDG 13 or no SDG)
    "environmental sustainability", "social and economic needs",
    "environmental, social", "sustainability framework"
]

# Penalty for SDG 12 when exclusion patterns found
SDG12_PENALTY = 0.40


def contains_sustainability_keywords(text: str) -> bool:
    """Check if text contains true sustainability keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in SDG12_SUSTAINABILITY_KEYWORDS)


def contains_exclusion_patterns(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains patterns that should NOT trigger SDG 12."""
    text_lower = text.lower()
    found = []
    for pattern in SDG12_EXCLUSION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern)
    return len(found) > 0, found


def apply_sdg12_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 12 bias corrections to alignment scores.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        correction_method: Which correction to apply

    Returns:
        Updated SDG scores with corrections applied
    """
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 12 not in scores:
        return scores

    text_lower = activity_text.lower()
    original_score = scores[12]['score']

    # Check for true sustainability keywords
    has_sustainability = contains_sustainability_keywords(activity_text)

    # Check for exclusion patterns
    has_exclusion, found_exclusions = contains_exclusion_patterns(activity_text)

    # Apply corrections
    if correction_method in ("penalty", "all"):
        if has_exclusion and not has_sustainability:
            # Penalize SDG 12 for financial activities
            scores[12]['score'] = max(0.0, original_score - SDG12_PENALTY)
            scores[12]['correction_applied'] = True

    # Boost SDG 16 for financial governance
    if correction_method in ("reassign", "all"):
        if has_exclusion:
            if 16 in scores:
                scores[16]['score'] = min(1.0, scores[16]['score'] + 0.15)

    return scores


def create_sdg12_corrector(method: str = "all", enabled: bool = True) -> callable:
    """Create an SDG 12 corrector function."""
    def corrector(
        activity_text: str,
        sdg_scores: Dict[int, Dict[str, Any]],
        activity_metadata: Dict[str, Any] = None
    ) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg12_corrections(activity_text, sdg_scores, method)
    return corrector