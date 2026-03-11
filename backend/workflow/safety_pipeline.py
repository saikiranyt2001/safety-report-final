from backend.agents.hazard_agent import identify_hazards
from backend.agents.risk_agent import assess_risk
from backend.agents.recommendation_agent import generate_recommendations
from backend.agents.compliance_agent import get_compliance_reference

def run_safety_workflow(data: dict):
    """
    Execute the AI Safety Workflow pipeline.
    """
    site_type = data.get("site_type", "construction")
    # Step 1: Hazard detection
    hazards = identify_hazards(site_type)
    # Step 2: Risk assessment
    risks = assess_risk(hazards)
    # Step 3: Control recommendations
    controls = generate_recommendations(hazards)
    # Step 4: Compliance regulations
    compliance = get_compliance_reference(hazards)
    # Step 5: Compile report
    report_data = {
        "company": data.get("company", ""),
        "location": data.get("location", ""),
        "inspection_date": data.get("inspection_date", ""),
        "hazards": hazards,
        "risks": risks,
        "controls": controls,
        "compliance": compliance,
        "recommendations": data.get("recommendations", ""),
        "review_date": data.get("review_date", "")
    }
    return report_data
