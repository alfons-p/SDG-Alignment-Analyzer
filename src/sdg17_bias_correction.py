"""SDG 17 Bias Correction Module.

Implements post-processing corrections for the known upward bias in SDG 17
(Partnerships for the Goals) alignment for local government documents.

Root Cause:
- Local government activities contain words like "council", "community",
  "volunteer", "local partnership" which incorrectly match SDG 17's
  broad "partnerships" concept
- sdgBERT doesn't cover SDG 17 (only 1-16), so it relies entirely on
  Sentence Transformer which has overly broad matching
- SDG 17 should ONLY match GLOBAL partnerships, not local governance

Correction Methods:
1. Score Multiplier: Penalize SDG 17 score when local governance keywords present
2. Explicit Re-assignment: Move to more appropriate SDG when local keywords found
3. Keyword-Based Threshold: Higher threshold for local partnership claims
4. Negative Keywords: Define what SDG 17 should NOT contain
"""

from typing import Dict, Any, List, Tuple, Optional


# Keywords that indicate LOCAL governance (NOT true SDG 17)
# These activities should NOT be classified as SDG 17
LOCAL_GOVERNANCE_KEYWORDS = [
    "council", "shire", "municipality", "shire council", "city council",
    "municipal", "local government", "councillor", "mayor", "councilor",
    "community hall", "town hall", "local council", "council staff",
    "council meeting", "council resolution", "council decision"
]

# Additional exclusion patterns for activities commonly misclassified as SDG 17
# These are NOT partnerships - they are infrastructure, community, or governance activities
SDG17_EXCLUSION_PATTERNS = [
    # Infrastructure activities
    "drainage upgrade", "drainage", "road upgrade", "road works",
    "infrastructure project", "construction", "upgrade completed",
    "bridge", "road", "transport", "infrastructure",
    "widening", "reinstatement", "land", "quary", "quarry",
    # Financial activities (SDG 16 or no SDG)
    "financial report", "financial statement", "evaluate", "presentation",
    "inventories", "receivables", "depreciation", "assets",
    "accounting", "valuation", "capitalised", "capitalised",
    "contributions plan", "section 7.11", "development contributions",
    # Community facilities (SDG 11)
    "library restoration", "library", "community centre", "community center",
    "community facility", "community hub", "community program",
    "community funding", "community scheme", "community project",
    # Disability/inclusion (SDG 10)
    "disability", "inclusion", "participation of people", "accessible",
    "people with disability", "diverse backgrounds",
    # Internal operations (SDG 16 or no SDG)
    "business continuity", "administration centre", "digital screens",
    "internal operations", "staff training", "employee",
    "motor vehicle", "commuting", "vehicle provided",
    # Generic governance
    "management services", "service delivery", "ongoing support",
    "strategic plan", "action plan", "compliance", "monitoring",
    # Administrative activities
    "reviewed", "assessed", "reporting period", "estimated",
    "costs", "subject to"
]

# Keywords that indicate TRUE global partnerships (correct SDG 17)
TRUE_SDG17_KEYWORDS = [
    "global partnership", "international cooperation", "overseas aid",
    "foreign aid", "development assistance", "united nations", "un dp",
    "global partnership for sustainable development", "north-south",
    "south-south cooperation", "technology transfer", "international development",
    "oda", "official development assistance", "multilateral", "bilateral aid",
    "least developed countries", "ldc", "developing nations", "third world",
    "international organization", "world bank", "asian development bank",
    "ausaid", "dfat", "international aid", "humanitarian", "overseas development",
    # Regional/inter-council partnerships (also valid SDG 17)
    "regional coordination", "strategic alliance", "joint initiative",
    "in partnership with", "in collaboration with", "partner councils",
    "constituent councils", "on behalf of councils", "inter-council",
    "multi-stakeholder", "public-private partnership", "funding scheme",
    "community funding scheme", "joint funding", "shared services",
    "regional partnership", "regional initiative"
]

# Secondary SDGs that should be boosted when local governance keywords found
# Based on analysis: SDG 11 (Sustainable Cities) and SDG 8 (Decent Work) are common
LOCAL_GOVERNANCE_SDG_REASSIGNMENT = {
    "community development": 11,
    "community services": 11,
    "community facility": 11,
    "local community": 11,
    "community facility": 11,
    "volunteer": 11,
    "volunteers": 11,
    "community event": 11,
    "community program": 11,
    "community project": 11,
    "community groups": 11,
    "local economic": 8,
    "local jobs": 8,
    "local business": 8,
    "employment": 8,
    "workforce": 8,
    "staff": 8,
    "training": 8,
    "skills": 8,
}

# Score multiplier for SDG 17 when local governance keywords found
SDG17_PENALTY_MULTIPLIER = 0.6  # Reduce score by 40%

# Additional penalty for activities that are clearly local governance
SDG17_LOCAL_GOVERNANCE_PENALTY = 0.25  # Additional 0.25 penalty

# Higher threshold for SDG 17 when local keywords found
SDG17_RAISED_THRESHOLD = 0.75  # Require higher confidence for local texts


def contains_local_keywords(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains local governance keywords.

    Args:
        text: Activity text to check

    Returns:
        Tuple of (has_local_keywords, found_keywords)
    """
    text_lower = text.lower()
    found = []

    for keyword in LOCAL_GOVERNANCE_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)

    return len(found) > 0, found


def contains_exclusion_patterns(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains patterns that should NOT trigger SDG 17.

    Args:
        text: Activity text to check

    Returns:
        Tuple of (has_exclusion, found_patterns)
    """
    text_lower = text.lower()
    found = []

    for pattern in SDG17_EXCLUSION_PATTERNS:
        if pattern in text_lower:
            found.append(pattern)

    return len(found) > 0, found


def contains_true_sdg17_keywords(text: str) -> bool:
    """
    Check if text contains TRUE global partnership keywords.

    Args:
        text: Activity text to check

    Returns:
        True if text contains true SDG 17 keywords
    """
    text_lower = text.lower()

    for keyword in TRUE_SDG17_KEYWORDS:
        if keyword in text_lower:
            return True

    return False


def apply_sdg17_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 17 bias corrections to alignment scores.

    More aggressive approach: Penalize SDG 17 by default unless TRUE partnership
    keywords are present. Local government documents rarely have true SDG 17 activities.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        correction_method: Which correction to apply
            - "multiplier": Apply score penalty
            - "reassign": Move to correct SDG
            - "threshold": Raise threshold for local texts
            - "negative": Use negative keywords
            - "all": Apply all corrections

    Returns:
        Updated SDG scores with corrections applied
    """
    # Make a copy to avoid modifying original
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 17 not in scores:
        return scores

    # Check for local governance keywords
    has_local, found_keywords = contains_local_keywords(activity_text)

    # Check for exclusion patterns (infrastructure, community, governance)
    has_exclusion, found_exclusions = contains_exclusion_patterns(activity_text)

    # Check for true SDG 17 keywords
    has_true_sdg17 = contains_true_sdg17_keywords(activity_text)

    original_sdg17_score = scores[17]['score']

    # NEW LOGIC: Penalize SDG 17 unless TRUE partnership keywords are present
    # This is more aggressive but necessary for local government documents

    if has_true_sdg17:
        # Has true partnership keywords - keep or boost SDG 17 score
        scores[17]['score'] = min(1.0, original_sdg17_score + 0.10)
        scores[17]['correction_applied'] = False
        return scores

    # No true SDG 17 keywords found - apply penalties
    text_lower = activity_text.lower()

    # Base penalty for local government activities (no global partnership)
    base_penalty = 0.30  # Reduce by 30% minimum

    # Additional penalty for specific false positive patterns
    if has_exclusion:
        # Has infrastructure, financial, or administrative patterns
        base_penalty += 0.20

    if has_local:
        # Has local governance keywords
        base_penalty += 0.15

    # Apply the penalty
    if correction_method in ("multiplier", "all"):
        # Apply multiplier first
        scores[17]['score'] = max(0.0, original_sdg17_score * SDG17_PENALTY_MULTIPLIER)
        # Then subtract additional penalty
        scores[17]['score'] = max(0.0, scores[17]['score'] - base_penalty)
        scores[17]['correction_applied'] = True

    # Method 2: Explicit Re-assignment - boost likely correct SDGs
    if correction_method in ("reassign", "all"):
        # Boost SDG 11 for community/infrastructure activities
        if any(kw in text_lower for kw in ["community", "volunteer", "hall", "facility",
                                            "road", "bridge", "infrastructure", "transport"]):
            if 11 in scores:
                scores[11]['score'] = min(1.0, scores[11]['score'] + 0.15)

        # Boost SDG 16 for governance/financial activities
        if any(kw in text_lower for kw in ["business continuity", "administration", "internal",
                                            "financial", "review", "audit", "statement",
                                            "governance", "compliance"]):
            if 16 in scores:
                scores[16]['score'] = min(1.0, scores[16]['score'] + 0.20)

        # Boost SDG 8 for employment/economic activities
        if any(kw in text_lower for kw in ["staff", "training", "employment", "job",
                                            "vehicle", "commuting"]):
            if 8 in scores:
                scores[8]['score'] = min(1.0, scores[8]['score'] + 0.15)

        # Boost SDG 10 for disability/inclusion activities
        if any(kw in text_lower for kw in ["disability", "inclusion", "accessible", "diverse"]):
            if 10 in scores:
                scores[10]['score'] = min(1.0, scores[10]['score'] + 0.15)

        # Boost SDG 9 for infrastructure activities
        if any(kw in text_lower for kw in ["road", "bridge", "infrastructure", "construction"]):
            if 9 in scores:
                scores[9]['score'] = min(1.0, scores[9]['score'] + 0.15)

    # Method 3: Keyword-Based Threshold - update is_aligned status
    if correction_method in ("threshold", "all"):
        # For activities without true SDG 17 keywords, require much higher threshold
        threshold = 0.85  # Very high threshold for SDG 17
        scores[17]['is_aligned'] = scores[17]['score'] >= threshold

    # Method 4: Negative Keywords - if very strong local signal, zero out SDG 17
    if correction_method in ("negative", "all"):
        # Strong local governance signal - significantly reduce SDG 17
        if len(found_keywords) >= 2 or has_exclusion:
            scores[17]['score'] = max(0.0, scores[17]['score'] - 0.3)

    return scores


def recalculate_top_sdg(
    scores: Dict[int, Dict[str, Any]]
) -> Tuple[int, float, str]:
    """
    Recalculate top SDG after corrections.

    Args:
        scores: Updated SDG scores

    Returns:
        Tuple of (top_sdg, top_score, sdg_name)
    """
    top_sdg = max(scores.keys(), key=lambda k: scores[k]['score'])
    top_score = scores[top_sdg]['score']
    sdg_name = scores[top_sdg].get('sdg_name', f'SDG {top_sdg}')

    return top_sdg, top_score, sdg_name


def create_sdg17_corrector(
    method: str = "all",
    enabled: bool = True
) -> callable:
    """
    Create an SDG 17 corrector function with specified settings.

    Args:
        method: Correction method to use
        enabled: Whether corrections are enabled

    Returns:
        Callable that applies corrections
    """
    def corrector(activity_text: str, sdg_scores: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg17_corrections(activity_text, sdg_scores, method)

    return corrector
