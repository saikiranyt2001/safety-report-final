# hazard_database.py
# Simple hazard database for RAG system

HAZARDS = [
    {
        "name": "fall from height",
        "risk": "high",
        "description": "Risk of falling from ladders, scaffolding, or elevated platforms."
    },
    {
        "name": "electrical shock",
        "risk": "high",
        "description": "Contact with exposed electrical wires or faulty equipment."
    },
    {
        "name": "machinery accident",
        "risk": "high",
        "description": "Injury caused by moving machine parts."
    },
    {
        "name": "slip and trip",
        "risk": "medium",
        "description": "Slippery floors or obstacles causing workers to fall."
    },
    {
        "name": "chemical exposure",
        "risk": "high",
        "description": "Exposure to hazardous chemicals causing burns or poisoning."
    }
]


def get_hazards(site_type=None):
    """
    Return hazard names for a given site type.
    Currently returns all hazards.
    """

    return [hazard["name"] for hazard in HAZARDS]


def get_hazard_details(hazard_name):
    """
    Return full hazard information
    """

    for hazard in HAZARDS:
        if hazard["name"] == hazard_name:
            return hazard

    return None