#done
# Risk Agent for Risk Assessment

RISK_MATRIX = {
    ("Rare","Minor"): "Low",
    ("Possible","Moderate"): "Medium",
    ("Likely","Major"): "High",
    ("Almost Certain","Fatal"): "Extreme"
}

LIKELIHOOD_SCORES = {
    "Rare":1,
    "Possible":2,
    "Likely":3,
    "Almost Certain":4
}

SEVERITY_SCORES = {
    "Minor":1,
    "Moderate":2,
    "Major":3,
    "Fatal":4
}

def classify_risk(score):
    if score <= 3:
        return "Low"
    elif score <= 6:
        return "Medium"
    elif score <= 9:
        return "High"
    else:
        return "Extreme"


def assess_risk(hazards):

    risks = {}

    hazard_list = hazards.get("hazards_detected", [])

    for h in hazard_list:

        likelihood = "Possible"
        severity = "Moderate"

        score = LIKELIHOOD_SCORES[likelihood] * SEVERITY_SCORES[severity]

        level = classify_risk(score)

        risks[h] = {
            "likelihood": likelihood,
            "severity": severity,
            "score": score,
            "level": level
        }

    return risks