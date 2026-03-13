import os

from backend.rag.regulation_loader import RegulationLoader


COMPLIANCE = {
    "working at height": [
        "WHS Regulation 78 – Falls",
        "ISO 45001 – Occupational Health and Safety",
    ],
    "electrical hazard": [
        "WHS Regulation 150 – Electrical Risks",
        "AS/NZS 3000 – Electrical Installations",
    ],
    "machine entanglement": [
        "WHS Regulation 208 – Plant Safety",
        "ISO 12100 – Machinery Safety",
    ],
    "chemical exposure": [
        "WHS Regulation 351 – Hazardous Chemicals",
        "GHS Chemical Safety Standards",
    ],
}


def _load_regulations() -> list[dict]:
    regulation_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "rag",
        "regulations.json",
    )
    loader = RegulationLoader(regulation_path)
    return loader.get_all()


def get_compliance_reference(hazards):
    references = []
    for hazard in hazards:
        refs = COMPLIANCE.get(str(hazard).lower(), ["General WHS Safety Duty"])
        references.extend(refs)
    return list(dict.fromkeys(references))


def find_matching_regulations(query: str) -> list[dict]:
    query_lower = query.lower().strip()
    matches = []
    for item in _load_regulations():
        haystack = " ".join(
            [
                str(item.get("regulation", "")),
                str(item.get("category", "")),
                str(item.get("reference", "")),
            ]
        ).lower()
        if query_lower and query_lower in haystack:
            matches.append(item)
    return matches[:5]


def suggest_recommended_action(rule_name: str, description: str = "") -> str:
    combined = f"{rule_name} {description}".lower()
    if "helmet" in combined or "ppe" in combined:
        return "Provide PPE immediately, brief workers, and enforce site entry checks."
    if "fall" in combined or "height" in combined:
        return "Install fall protection controls and stop elevated work until compliant."
    if "fire" in combined or "extinguisher" in combined:
        return "Restore fire equipment access and verify emergency readiness today."
    if "electrical" in combined:
        return "Isolate electrical hazard, inspect panels, and verify lockout/tagout compliance."
    return "Investigate the violation, apply corrective action, and verify compliance evidence."


def evaluate_rule(rule_name: str, observation: str = "") -> dict:
    combined = f"{rule_name} {observation}".lower()
    violation_terms = [
        "no helmet",
        "missing ppe",
        "blocked exit",
        "fall hazard",
        "exposed wire",
        "spill",
        "violation",
        "not compliant",
    ]
    status = "violated" if any(term in combined for term in violation_terms) else "compliant"
    return {
        "status": status,
        "recommended_action": suggest_recommended_action(rule_name, observation),
        "matched_regulations": find_matching_regulations(rule_name) or find_matching_regulations(observation),
    }
