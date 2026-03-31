"""SDG 11 Bias Correction Module.

Implements post-processing corrections for the known upward bias in SDG 11
(Sustainable Cities and Communities) alignment for local government documents.

Root Cause:
- Local government documents constantly mention "community", "city", "town"
- The word "sustainable" appears in many contexts beyond actual SDG 11 work
- sdgBERT and Sentence Transformer match too broadly on urban-related terms
- Many activities are passive descriptions without action verbs

Correction Approach (REVISED - no strict AND):
- Penalize scores when lacking sustainability terms (rather than eliminating)
- Apply negative keyword penalty (generic community activities)
- Allow SDG 11 to remain prominent but not dominant

This is a "demotion" rather than "elimination" approach.
"""

from typing import Dict, Any, List, Tuple, Optional


# Sustainability-related terms that indicate TRUE SDG 11
# These act as "pass" markers - if present, SDG 11 is likely valid
SDG11_SUSTAINABILITY_TERMS = [
    # 11.1 - Housing
    "affordable housing", "slum upgrading", "informal settlement", "adequate housing",
    "housing services", "homelessness", "housing affordability", "housing program",
    # 11.2 - Transport
    "public transport", "sustainable transport", "transport accessibility",
    "mass transit", "bus rapid transit", "light rail", "metro", "transport system",
    # 11.3 - Urban planning
    "urban planning", "city planning", "land use", "zoning",
    "participatory planning", "integrated settlement", "inclusive urbanization",
    "urban growth", "settlement planning",
    # 11.4 - Heritage
    "cultural heritage", "natural heritage", "heritage preservation",
    "heritage conservation", "historic preservation", "heritage site",
    # 11.5 - Disasters
    "disaster risk", "disaster resilience", "emergency management",
    "flood mitigation", "bushfire", "climate adaptation", "disaster recovery",
    # 11.6 - Environment
    "air quality", "municipal waste", "waste management", "pm2.5",
    "particulate matter", "waste collection", "controlled disposal",
    "environmental impact", "urban environment",
    # 11.7 - Public spaces
    "green space", "public space", "urban park", "playground",
    "accessible space", "inclusive public space", "open space",
    # General sustainability
    "resilient", "sustainable city", "sustainable urban", "climate resilient",
    "net zero", "carbon neutral", "energy efficient", "liveable",
    "sustainable settlement", "urban sustainability"
]

# Negative keywords - indicate content is likely NOT true SDG 11
# These are generic community activities that should be demoted
SDG11_NEGATIVE_KEYWORDS = [
    # Generic community services (NOT SDG 11)
    "community service", "community hall", "community centre",
    "community event", "community festival", "community program",
    "community group", "volunteer", "community volunteer",
    "community meeting", "community activity",
    # Generic council services (NOT SDG 11 - governance)
    "council meeting", "council decision", "council resolution",
    "administrative", "business license", "rate collection",
    "council staff", "council operations",
    "provides services for residents", "provides services for ratepayers",
    "services for residents and ratepayers",
    # Governance activities (should be SDG 16)
    "internal review", "business continuity", "management services",
    "administration centre", "governance framework", "transparency",
    "internal operations", "financial statements",
    "strong and ethical civic leadership", "civic leadership",
    # Financial activities (should be SDG 16 or no SDG)
    "financial report", "financial sustainability", "audit",
    "going concern", "annual report", "financial position",
    "revenue ratio", "controlled revenue",
    "revenue and rating plan", "rating plan", "rating structure",
    # IT and systems (should be SDG 9 or no SDG)
    "information technology", "it systems", "erp system",
    "database", "software", "technology platform",
    # Strategic planning (should be SDG 16 or no SDG)
    "strategic plan", "corporate plan", "annual plan",
    "strategic framework", "delivery program",
    # Generic community activities (NOT SDG 11)
    "community event", "community hub", "community program",
    "disability inclusion action plan", "diap",
    # Generic social services (NOT SDG 11 - should be SDG 1, 3, 5, 10)
    "social service", "welfare", "aged care", "child care",
    "disability service", "community care", "social support",
    # Generic recreation (NOT SDG 11 unless about public space)
    "recreational", "sports club", "leisure centre", "gym",
    "fitness program", "sports program",
]

# Lighter penalties - demotion not elimination
SDG11_PENALTY_NO_SUSTAINABILITY = 0.35  # Demote if no sustainability terms (was 0.15)
SDG11_PENALTY_NEGATIVE_KEYWORD = 0.40  # Demote for negative keywords (was 0.20)
SDG11_BONUS_WITH_SUSTAINABILITY = 0.10  # Boost if has sustainability terms


def check_co_requirements(text: str) -> Dict[str, bool]:
    """
    Check if text meets SDG 11 co-requirements.

    Args:
        text: Activity text to check

    Returns:
        Dict with: has_action, has_community, has_sustainability, has_negative
    """
    text_lower = text.lower()

    # Check for action-related content (already calculated in activity)
    # We'll check for action verbs in text as backup
    action_indicators = [
        "implement", "deliver", "complete", "construct", "build",
        "establish", "create", "develop", "install", "upgrade",
        "provide", "manage", "maintain", "operate", "run",
        "funded", "completed", "delivered", "established", "created"
    ]
    has_action = any(verb in text_lower for verb in action_indicators)

    # Check for community/city terms
    community_terms = ["community", "city", "urban", "town", "municipal", "settlement"]
    has_community = any(term in text_lower for term in community_terms)

    # Check for sustainability terms
    has_sustainability = any(
        term in text_lower for term in SDG11_SUSTAINABILITY_TERMS
    )

    # Check for negative keywords
    has_negative = any(
        kw in text_lower for kw in SDG11_NEGATIVE_KEYWORDS
    )

    return {
        "has_action": has_action,
        "has_community": has_community,
        "has_sustainability": has_sustainability,
        "has_negative": has_negative
    }


def apply_sdg11_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    activity_metadata: Optional[Dict[str, Any]] = None,
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 11 bias corrections to alignment scores.

    This is a "demotion" approach - apply penalties for false indicators
    and bonuses for true indicators, rather than strict requirements.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        activity_metadata: Optional metadata from activity extraction
        correction_method: Which correction to apply
            - "bonus": Apply bonus/penalty to scores
            - "reassign": Boost other SDGs for false positives
            - "all": Apply all corrections

    Returns:
        Updated SDG scores with corrections applied
    """
    # Make a copy to avoid modifying original
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    if 11 not in scores:
        return scores

    text_lower = activity_text.lower()
    original_sdg11_score = scores[11]['score']

    # Check for sustainability terms (pass markers)
    has_sustainability = any(
        term in text_lower for term in SDG11_SUSTAINABILITY_TERMS
    )

    # Check for negative keywords (demotion signals)
    has_negative = any(
        kw in text_lower for kw in SDG11_NEGATIVE_KEYWORDS
    )

    # Apply bonuses and penalties
    if correction_method in ("bonus", "all"):
        # Bonus: Boost SDG 11 if has sustainability terms
        if has_sustainability:
            scores[11]['score'] = min(1.0, original_sdg11_score + SDG11_BONUS_WITH_SUSTAINABILITY)
        # Penalty: Demote if has negative keywords but no sustainability
        elif has_negative:
            scores[11]['score'] = max(0.0, original_sdg11_score - SDG11_PENALTY_NEGATIVE_KEYWORD)
        # Penalty: Light demotion if no sustainability terms at all
        else:
            scores[11]['score'] = max(0.0, original_sdg11_score - SDG11_PENALTY_NO_SUSTAINABILITY)

    # Re-assignment: Boost other SDGs for content that was wrongly classified as SDG 11
    if correction_method in ("reassign", "all"):
        # Boost SDG 3 for health-related community activities
        if any(kw in text_lower for kw in ["health", "medical", "hospital", "clinic"]):
            if 3 in scores:
                scores[3]['score'] = min(1.0, scores[3]['score'] + 0.10)

        # Boost SDG 1 for social welfare activities
        if any(kw in text_lower for kw in ["welfare", "social service", "support service"]):
            if 1 in scores:
                scores[1]['score'] = min(1.0, scores[1]['score'] + 0.10)

        # Boost SDG 8 for workforce/employment
        if any(kw in text_lower for kw in ["employment", "job", "workforce", "training"]):
            if 8 in scores:
                scores[8]['score'] = min(1.0, scores[8]['score'] + 0.10)

        # Boost SDG 3 for recreation/leisure
        if any(kw in text_lower for kw in ["recreational", "sport", "fitness", "leisure"]):
            if 3 in scores:
                scores[3]['score'] = min(1.0, scores[3]['score'] + 0.10)

        # Boost SDG 16 for governance activities
        if any(kw in text_lower for kw in ["internal review", "business continuity", "governance",
                                              "transparency", "administration", "financial statements"]):
            if 16 in scores:
                scores[16]['score'] = min(1.0, scores[16]['score'] + 0.15)

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


def create_sdg11_corrector(
    method: str = "all",
    enabled: bool = True
) -> callable:
    """
    Create an SDG 11 corrector function with specified settings.

    Args:
        method: Correction method to use
        enabled: Whether corrections are enabled

    Returns:
        Callable that applies corrections
    """
    def corrector(
        activity_text: str,
        sdg_scores: Dict[int, Dict[str, Any]],
        activity_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[int, Dict[str, Any]]:
        if not enabled:
            return sdg_scores
        return apply_sdg11_corrections(
            activity_text, sdg_scores, activity_metadata, method
        )

    return corrector
