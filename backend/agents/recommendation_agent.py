
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

    hazard_key = hazard.lower()

    controls = []

    if hazard_key in RECOMMENDATIONS:

        hazard_controls = RECOMMENDATIONS[hazard_key]

        for level in HIERARCHY_OF_CONTROLS:
            if level in hazard_controls:
                controls.append({
                    "level": level,
                    "action": hazard_controls[level]
                })

    else:

        controls.append({
            "level": "PPE",
            "action": DEFAULT_CONTROLS["PPE"]
        })

    return {
        "hazard": hazard,
        "controls": controls
    }
