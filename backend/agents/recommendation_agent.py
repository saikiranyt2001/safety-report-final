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

def generate_recommendations(hazards):
    recs = []
    for hazard in hazards:
        controls = RECOMMENDATIONS.get(hazard, {})
        rec = {"hazard": hazard, "controls": {}}
        for level in HIERARCHY_OF_CONTROLS:
            if level in controls:
                rec["controls"][level] = controls[level]
            elif level in DEFAULT_CONTROLS:
                rec["controls"][level] = DEFAULT_CONTROLS[level]
        recs.append(rec)
    return recs

#done
