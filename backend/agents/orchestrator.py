from backend.agents.hazard_agent import identify_hazards
from backend.agents.risk_agent import assess_risk
from backend.agents.recommendation_agent import recommend_controls
from backend.agents.safety_score_agent import calculate_safety_score
from backend.agents.risk_matrix_agent import generate_risk_matrix


def run_safety_pipeline(site_type, site_data):

    # Step 1: Detect hazards
    hazards = identify_hazards(site_type)

    risk_results = []
    recommendations = []

    # Step 2: Assess risk for each hazard
    for hazard in hazards:

        risk_result = assess_risk(
            site_data["likelihood"],
            site_data["severity"]
        )

        risk_results.append({
            "hazard": hazard,
            "risk": risk_result
        })

        # Step 3: Generate recommendation
        rec = recommend_controls(hazard, risk_result)
        recommendations.append(rec)

    # Extract values for matrix + score
    severity = site_data["severity"]
    likelihood = site_data["likelihood"]

    # Step 4: Generate risk matrix
    risk_matrix = generate_risk_matrix(severity, likelihood)

    # Step 5: Calculate safety score
    safety_score = calculate_safety_score(severity, likelihood)

    return {
        "site_type": site_type,
        "hazards": hazards,
        "risk_results": risk_results,
        "recommendations": recommendations,
        "safety_score": safety_score,
        "risk_matrix": risk_matrix
    }