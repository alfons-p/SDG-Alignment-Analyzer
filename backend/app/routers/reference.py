"""Reference router — SDG definitions and metadata."""

from fastapi import APIRouter

from src.config.sdg_definitions import SDG_DEFINITIONS, SDG_COLORS, SDG_DATA

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/sdgs")
def get_sdgs():
    """Return all 17 SDGs with full metadata."""
    return {
        "sdgs": [
            {
                "number": sdg_num,
                "name": data["name"],
                "short_description": data["short_description"],
                "description": data["description"],
                "keywords": data.get("keywords", []),
                "local_gov_keywords": data.get("local_gov_keywords", []),
                "targets": data.get("targets", []),
                "indicators": data.get("indicators", []),
                "color": data["color"],
            }
            for sdg_num, data in SDG_DEFINITIONS.items()
        ]
    }


@router.get("/sdgs/colors")
def get_sdg_colors():
    return {"colors": SDG_COLORS}


@router.get("/sdgs/simple")
def get_sdg_simple():
    """Return minimal SDG data (name + description) for UI display."""
    return {"sdgs": SDG_DATA}
