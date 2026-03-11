from agents.hazard_agent import identify_hazards
from agents.risk_agent import assess_risk
from agents.recommendation_agent import generate_recommendations

def run_safety_pipeline(site_type, site_data):
    hazards = identify_hazards(site_type, site_data)
    risk = assess_risk(hazards)
    recommendations = []
    # Loop through hazards and call recommend_controls with correct arguments
    from agents.recommendation_agent import recommend_controls
    for hazard in hazards.get("hazards_detected", []):
        controls_data = risk.get(hazard, {}) if isinstance(risk, dict) else {}
        rec = recommend_controls(hazard, controls_data)
        recommendations.append(rec)
    return {
        "hazards": hazards,
        "risk": risk,
        "recommendations": recommendations
    }
