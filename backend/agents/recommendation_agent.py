# Recommendation Agent

HIERARCHY_OF_CONTROLS = [
    "Elimination",
    "Substitution",
    "Engineering Controls",
    "Administrative Controls",
    "PPE"
]

RECOMMENDATIONS = {
    "working at height": {
        "Engineering Controls": "Install guardrails",
        "Administrative Controls": "Permit to work",
        "PPE": "Safety harness"
    },
    "electrical hazard": {
        "Engineering Controls": "De-energize circuits before work",
        "Administrative Controls": "Lockout/tagout procedures",
        "PPE": "Insulated gloves"
    },
    "machine entanglement": {
        "Engineering Controls": "Install machine guards",
        "Administrative Controls": "Operator training",
        "PPE": "Protective gloves"
    }
}

DEFAULT_CONTROLS = {
    "PPE": "Use appropriate safety equipment"
}


def recommend_controls(hazard, risk_data):

    controls = []

    if hazard.lower() == "fire":
        controls = [
            "Install fire extinguishers",
            "Provide fire safety training",
            "Maintain clear evacuation routes"
        ]

    elif hazard.lower() == "fall":
        controls = [
            "Use safety harnesses",
            "Install guardrails",
            "Provide fall protection training"
        ]

    elif hazard.lower() == "chemical":
        controls = [
            "Use proper PPE",
            "Ensure chemical labeling",
            "Provide ventilation systems"
        ]

    else:
        controls = [
            "Follow standard safety procedures",
            "Conduct regular inspections"
        ]

    return {
        "hazard": hazard,
        "controls": controls
    }
