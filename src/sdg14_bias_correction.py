"""SDG 14 Bias Correction Module.

Implements post-processing corrections for the known upward bias in SDG 14
(Life Below Water) alignment for local government documents.

Root Cause:
- Road names often contain coastal terms: "South Beach Road", "Coastal Highway"
- Town names in coastal areas: "Brunswick Heads", "Byron Bay", "Shellharbour"
- Infrastructure projects near water trigger false SDG 14 matches
- The word "beach", "coast", "bay" in names triggers semantic matches
- These are NOT actual marine/coastal conservation activities

Examples of FALSE POSITIVES:
- "Improvements on South Beach Road" → SDG 14 (wrong, should be SDG 9 or 11)
- "Brunswick Heads town center upgrade" → SDG 14 (wrong, should be SDG 11)
- "Coastal Road maintenance" → SDG 14 (wrong, should be SDG 9)

Correction Methods:
1. Road/Street Detection: Penalize SDG 14 when road/street terms present
2. Infrastructure Keywords: Boost SDG 9/11 when infrastructure terms present
3. Town Name Detection: Identify coastal town names that shouldn't trigger SDG 14
4. Marine Conservation Keywords: Boost SDG 14 when actual marine keywords present
"""

from typing import Dict, Any, List, Tuple, Optional
import re


# Road/street indicators - if these are present with "beach"/"coast"/"bay",
# it's likely a road name, not actual marine activity
ROAD_INDICATORS = [
    "road", "street", "ave", "avenue", "drive", "way", "lane", "place",
    "highway", "motorway", "freeway", "boulevard", "circuit", "court",
    "parade", "crescent", "close", "trail", "track", "route",
    "improvements", "upgrade", "maintenance", "construction", "works",
    "project", "redevelopment", "widening", "resurfacing", "path", "pathway"
]

# Infrastructure/construction keywords that indicate NOT SDG 14
INFRASTRUCTURE_KEYWORDS = [
    "road", "street", "bridge", "pathway", "footpath", "cycleway",
    "drainage", "sewer", "water main", "pipe", "culvert",
    "construction", "upgrade", "improvement", "redevelopment",
    "maintenance", "repair", "resurface", "widening", "extension",
    "parking", "car park", "traffic", "transport", "bus stop",
    "footpath", "walkway", "boardwalk", "promenade", "esplanade"
]

# Australian coastal town/place names that should NOT trigger SDG 14
# when used as location names (not as marine activities)
COASTAL_PLACE_NAMES = [
    # NSW coastal towns
    "byron bay", "byron", "brunswick heads", "brunswick", "ballina",
    "coffs harbour", "coffs", "port macquarie", "port stephens", "newcastle",
    "wollongong", "shellharbour", "sutherland", "cronulla", "bondi",
    "coogee", "manly", "dee why", "narrabeen", "terrigal", "the entrance",
    "batemans bay", "merimbula", "eden", "yamba", "woolgoolga",
    "sawtell", "nambucca", "macleay", "hastings", "tweed heads",
    "cabarita", "kingscliff", "pottsville", "lennox head", "evans head",
    # VIC coastal towns
    "geelong", "torquay", "lorne", "apollo bay", "queenscliff",
    "sorrento", "mornington", "frankston", "warrnambool",
    "phillip island", "wilsons promontory", "lakes entrance", "sale",
    # QLD coastal towns
    "gold coast", "sunshine coast", "noosa", "maroochydore", "caloundra",
    "hervey bay", "gladstone", "rockhampton", "townsville", "cairns",
    # SA coastal areas
    "glenelg", "victor harbor", "port lincoln", "whyalla",
    # WA coastal areas
    "fremantle", "perth", "mandurah", "bunbury", "geraldton",
    # Tasmania
    "hobart", "launceston", "devonport", "burnie",
    # Generic coastal terms used in names
    "heads", "point", "bay", "beach", "cove", "haven"
]

# TRUE SDG 14 keywords - these SHOULD match SDG 14
# Only match when discussing actual marine/coastal conservation
TRUE_SDG14_KEYWORDS = [
    # Marine conservation activities
    "marine conservation", "marine protected area", "marine park",
    "marine sanctuary", "marine reserve", "marine biodiversity",
    "ocean conservation", "marine ecosystem", "coral reef", "seagrass",
    "mangrove", "saltmarsh", "wetland restoration", "estuary restoration",

    # Water quality specific to marine
    "marine pollution", "ocean pollution", "marine debris",
    "coastal water quality", "estuarine water quality",
    "stormwater discharge", "marine water quality",

    # Fishing/marine resources
    "sustainable fishing", "fisheries management", "fishing sustainability",
    "marine resources", "aquaculture", "oyster", "prawn fishery",
    "recreational fishing management", "commercial fishing",

    # Coastal protection/management
    "coastal protection", "coastal erosion", "coastal management",
    "coastal hazard", "sea level rise", "coastal adaptation",
    "beach nourishment", "dune restoration", "foreshore protection",

    # Marine monitoring
    "marine monitoring", "coastal monitoring", "water quality monitoring",
    "marine biodiversity survey", "marine health", "ocean health",

    # International marine
    "international waters", "marine biodiversity beyond",

    # Specific marine habitats
    "intertidal", "subtidal", "pelagic", "benthic",
    "rocky reef", "kelp forest", "sponge garden", "sea floor"
]

# Non-marine coastal activities - these should NOT match SDG 14
NON_MARINE_COASTAL_KEYWORDS = [
    # Road/infrastructure
    "road", "street", "highway", "bridge", "path", "walkway",
    "parking", "car park", "traffic", "transport",

    # Buildings/facilities near coast
    "building", "facility", "centre", "club", "hotel", "restaurant",
    "cafe", "shop", "retail", "community facility",

    # Events/tourism
    "festival", "event", "market", "tourism", "visitor",

    # General coastal usage (not conservation)
    "coastal access", "public access", "viewing platform",
    "lookout", "picnic", "barbecue", "bbq"
]

# Penalties and bonuses
SDG14_PENALTY_ROAD_NAME = 0.40  # Strong penalty for road names
SDG14_PENALTY_INFRASTRUCTURE = 0.30  # Penalty for infrastructure activities
SDG14_PENALTY_PLACE_NAME = 0.25  # Penalty for coastal place names
SDG14_BONUS_MARINE_KEYWORD = 0.15  # Bonus for true marine keywords

# SDGs to boost when SDG 14 is penalized
INFRASTRUCTURE_SDG_BOOST = {
    9: 0.15,   # Industry, Innovation, Infrastructure
    11: 0.10,  # Sustainable Cities
}


def contains_road_pattern(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains road/street names with coastal keywords.

    Detects patterns like:
    - "South Beach Road"
    - "Coastal Highway"
    - "Bay Street"
    - "improvements on Beach Road"

    Args:
        text: Activity text to check

    Returns:
        Tuple of (is_road_pattern, found_patterns)
    """
    text_lower = text.lower()
    found_patterns = []

    # Pattern 1: Coastal keyword followed by road indicator
    # e.g., "Beach Road", "Coastal Highway", "Bay Street"
    coastal_keywords = ["beach", "coast", "coastal", "bay", "harbour", "harbor",
                        "head", "heads", "point", "cove", "haven"]

    for coastal in coastal_keywords:
        for road in ROAD_INDICATORS:
            # Check for "Coastal Road" pattern
            pattern1 = f"{coastal} {road}"
            if pattern1 in text_lower:
                found_patterns.append(pattern1)

            # Check for "Road improvements" near coastal
            # e.g., "improvements on Beach Road"
            if road in text_lower and coastal in text_lower:
                # Check if they're in proximity (within 5 words)
                words = text_lower.split()
                for i, word in enumerate(words):
                    if coastal in word:
                        for j in range(max(0, i-5), min(len(words), i+6)):
                            if words[j] in ROAD_INDICATORS:
                                found_patterns.append(f"{coastal}...{words[j]}")
                                break

    # Pattern 2: Infrastructure verbs with coastal location
    # e.g., "upgrading South Beach Road", "improvements at Brunswick Heads"
    infrastructure_verbs = ["improve", "upgrade", "construct", "build", "repair",
                           "maintain", "redevelop", "widen", "extend"]

    for verb in infrastructure_verbs:
        if verb in text_lower:
            for coastal in coastal_keywords:
                if coastal in text_lower:
                    # Check for road indicators nearby
                    if any(road in text_lower for road in ROAD_INDICATORS):
                        found_patterns.append(f"{verb}...{coastal}")

    return len(found_patterns) > 0, list(set(found_patterns))


def contains_coastal_place_name(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains coastal place names that should NOT trigger SDG 14.

    Args:
        text: Activity text to check

    Returns:
        Tuple of (has_place_name, found_places)
    """
    text_lower = text.lower()
    found_places = []

    for place in COASTAL_PLACE_NAMES:
        if place in text_lower:
            # Check if it's used as a location name (not marine activity)
            # Look for location indicators
            location_indicators = ["at", "in", "near", "of", "for"]
            words = text_lower.split()

            for i, word in enumerate(words):
                if place in word:
                    # Check context for location usage
                    context_before = " ".join(words[max(0, i-3):i])
                    context_after = " ".join(words[i+1:min(len(words), i+4)])

                    # If road/infrastructure terms nearby, it's a place name
                    if any(road in context_before or road in context_after for road in ROAD_INDICATORS):
                        found_places.append(place)
                        break
                    # If location indicator before, it's a place name
                    if any(loc in context_before for loc in location_indicators):
                        found_places.append(place)
                        break

    return len(found_places) > 0, list(set(found_places))


def has_true_marine_keywords(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains TRUE SDG 14 keywords indicating actual marine conservation.

    Args:
        text: Activity text to check

    Returns:
        Tuple of (has_marine_keywords, found_keywords)
    """
    text_lower = text.lower()
    found = []

    for keyword in TRUE_SDG14_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)

    return len(found) > 0, found


def has_infrastructure_keywords(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains infrastructure keywords that indicate NOT SDG 14.

    Args:
        text: Activity text to check

    Returns:
        Tuple of (has_infra_keywords, found_keywords)
    """
    text_lower = text.lower()
    found = []

    for keyword in INFRASTRUCTURE_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)

    return len(found) > 0, found


def apply_sdg14_corrections(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]],
    activity_metadata: Optional[Dict[str, Any]] = None,
    correction_method: str = "all"
) -> Dict[int, Dict[str, Any]]:
    """
    Apply SDG 14 bias corrections to alignment scores.

    This addresses false positives from:
    - Road names containing coastal keywords (South Beach Road)
    - Town names in coastal areas (Brunswick Heads)
    - Infrastructure projects near water

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary
        activity_metadata: Optional metadata from activity extraction
        correction_method: Which correction to apply
            - "road_penalty": Penalize for road names
            - "infrastructure_penalty": Penalize for infrastructure
            - "place_penalty": Penalize for coastal place names
            - "marine_bonus": Boost for true marine keywords
            - "reassign": Boost SDG 9/11 when SDG 14 penalized
            - "all": Apply all corrections

    Returns:
        Updated SDG scores with corrections applied
    """
    # Make a copy to avoid modifying original
    scores = {k: v.copy() for k, v in sdg_scores.items()}

    # Only process if SDG 14 is present and has a meaningful score
    # Use lower threshold (0.2) to catch ensemble scores that combine corrected ST
    # with uncorrected sdgBERT predictions
    if 14 not in scores or scores[14]["score"] < 0.2:
        return scores

    original_score = scores[14]["score"]
    total_penalty = 0.0
    reasons = []

    # Check for road name patterns
    has_road_pattern, road_patterns = contains_road_pattern(activity_text)
    if has_road_pattern:
        total_penalty += SDG14_PENALTY_ROAD_NAME
        reasons.append(f"Road name pattern: {road_patterns[:3]}")

    # Check for infrastructure keywords
    has_infra, infra_keywords = has_infrastructure_keywords(activity_text)
    if has_infra:
        total_penalty += SDG14_PENALTY_INFRASTRUCTURE
        reasons.append(f"Infrastructure keywords: {infra_keywords[:3]}")

    # Check for coastal place names
    has_place, places = contains_coastal_place_name(activity_text)
    if has_place:
        total_penalty += SDG14_PENALTY_PLACE_NAME
        reasons.append(f"Coastal place name: {places[:3]}")

    # Check for TRUE marine keywords (this should BOOST SDG 14)
    has_marine, marine_keywords = has_true_marine_keywords(activity_text)

    # Apply corrections based on method
    apply_road = correction_method in ["road_penalty", "all"]
    apply_infra = correction_method in ["infrastructure_penalty", "all"]
    apply_place = correction_method in ["place_penalty", "all"]
    apply_marine = correction_method in ["marine_bonus", "all"]
    apply_reassign = correction_method in ["reassign", "all"]

    # Calculate final penalty (capped to not go below 0)
    if apply_road and has_road_pattern:
        scores[14]["score"] = max(0.0, scores[14]["score"] - SDG14_PENALTY_ROAD_NAME)

    if apply_infra and has_infra:
        scores[14]["score"] = max(0.0, scores[14]["score"] - SDG14_PENALTY_INFRASTRUCTURE)

    if apply_place and has_place:
        scores[14]["score"] = max(0.0, scores[14]["score"] - SDG14_PENALTY_PLACE_NAME)

    # Boost for TRUE marine keywords
    if apply_marine and has_marine:
        scores[14]["score"] = min(1.0, scores[14]["score"] + SDG14_BONUS_MARINE_KEYWORD)
        # Remove penalties if this is actual marine conservation
        if len(marine_keywords) >= 2:  # Multiple marine keywords = strong signal
            scores[14]["score"] = original_score  # Restore original score

    # Reassign to SDG 9 (Infrastructure) or SDG 11 (Sustainable Cities)
    # when SDG 14 is penalized
    if apply_reassign and scores[14]["score"] < original_score:
        # Boost SDG 9 and 11
        for sdg_num, boost in INFRASTRUCTURE_SDG_BOOST.items():
            if sdg_num in scores:
                scores[sdg_num]["score"] = min(1.0, scores[sdg_num]["score"] + boost)

    # Add correction metadata
    if total_penalty > 0:
        scores[14]["correction_applied"] = True
        scores[14]["correction_reasons"] = reasons
        scores[14]["original_score"] = original_score
        scores[14]["penalty_amount"] = original_score - scores[14]["score"]
    elif has_marine:
        scores[14]["correction_applied"] = True
        scores[14]["correction_reasons"] = [f"True marine keywords: {marine_keywords[:3]}"]
        scores[14]["original_score"] = original_score

    return scores


def get_correction_summary(
    activity_text: str,
    sdg_scores: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Get a summary of SDG 14 corrections that would be applied.

    Useful for debugging and understanding why corrections are applied.

    Args:
        activity_text: The activity description
        sdg_scores: Current SDG scores dictionary

    Returns:
        Dictionary with correction analysis
    """
    has_road, road_patterns = contains_road_pattern(activity_text)
    has_infra, infra_keywords = has_infrastructure_keywords(activity_text)
    has_place, places = contains_coastal_place_name(activity_text)
    has_marine, marine_keywords = has_true_marine_keywords(activity_text)

    original_score = sdg_scores.get(14, {}).get("score", 0.0)

    # Calculate what the corrected score would be
    corrected_score = original_score
    if has_road:
        corrected_score = max(0.0, corrected_score - SDG14_PENALTY_ROAD_NAME)
    if has_infra:
        corrected_score = max(0.0, corrected_score - SDG14_PENALTY_INFRASTRUCTURE)
    if has_place:
        corrected_score = max(0.0, corrected_score - SDG14_PENALTY_PLACE_NAME)
    if has_marine:
        corrected_score = min(1.0, corrected_score + SDG14_BONUS_MARINE_KEYWORD)

    return {
        "original_sdg14_score": original_score,
        "corrected_sdg14_score": corrected_score,
        "has_road_pattern": has_road,
        "road_patterns": road_patterns,
        "has_infrastructure_keywords": has_infra,
        "infrastructure_keywords": infra_keywords,
        "has_coastal_place_name": has_place,
        "place_names": places,
        "has_true_marine_keywords": has_marine,
        "marine_keywords": marine_keywords,
        "would_apply_correction": corrected_score != original_score,
        "recommendation": "SDG 14 penalty" if corrected_score < original_score else
                         "SDG 14 boost" if corrected_score > original_score else
                         "No change"
    }