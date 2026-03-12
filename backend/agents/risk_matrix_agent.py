def generate_risk_matrix(severity: int, likelihood: int):
    """
    Generate risk matrix classification
    """
    score = severity * likelihood
    if score <= 4:
        level = "Low"
    elif score <= 9:
        level = "Medium"
    elif score <= 16:
        level = "High"
    else:
        level = "Extreme"
    return {
        "severity": severity,
        "likelihood": likelihood,
        "risk_score": score,
        "risk_level": level
    }
