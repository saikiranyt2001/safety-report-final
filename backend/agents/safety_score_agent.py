# Safety Score Agent

# Implement logic for AI-based safety scoring here.
# Example: analyze project/report data and return a safety score.

def calculate_safety_score(severity: int, likelihood: int):

    """
    Calculate safety score from severity and likelihood
    Higher risk = lower score
    """

    risk = severity * likelihood

    score = 100 - (risk * 4)

    if score < 0:
        score = 0

    if score > 100:
        score = 100

    return score
