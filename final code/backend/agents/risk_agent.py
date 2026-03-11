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
    for h in hazards:
        # Example: each hazard should have likelihood and severity
        likelihood = h.get("likelihood", "Possible") if isinstance(h, dict) else "Possible"
        severity = h.get("severity", "Moderate") if isinstance(h, dict) else "Moderate"
        score = LIKELIHOOD_SCORES.get(likelihood,0) * SEVERITY_SCORES.get(severity,0)
        level = RISK_MATRIX.get((likelihood,severity), classify_risk(score))
        risks[h if not isinstance(h, dict) else h.get("name", str(h))] = {
            "likelihood": likelihood,
            "severity": severity,
            "score": score,
            "level": level
        }
    return risks
