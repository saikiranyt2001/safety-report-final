def check_compliance():
    # TODO: Define or import get_compliance_checklist
    checklist = []  # Placeholder: replace with actual checklist logic
    results = {}
    for item in checklist:
        results[item] = "✓" if validate_rule(item) else "✗"
    return results

def validate_rule(rule):
    # placeholder logic
    return True
# Compliance Agent

COMPLIANCE = {
    "working at height": [
        "WHS Regulation 78 – Falls",
        "ISO 45001 – Occupational Health and Safety"
    ],
    "electrical hazard": [
        "WHS Regulation 150 – Electrical Risks",
        "AS/NZS 3000 – Electrical Installations"
    ],
    "machine entanglement": [
        "WHS Regulation 208 – Plant Safety",
        "ISO 12100 – Machinery Safety"
    ],
    "chemical exposure": [
        "WHS Regulation 351 – Hazardous Chemicals",
        "GHS Chemical Safety Standards"
    ]
}

def get_compliance_reference(hazards):
    references = []
    for h in hazards:
        refs = COMPLIANCE.get(h, ["General WHS Safety Duty"])
        references.extend(refs)
    return list(set(references))

#done
