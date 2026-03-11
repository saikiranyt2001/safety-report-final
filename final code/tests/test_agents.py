
from safety_report_trial.backend.agents.safety_advisor_agent import analyze_site

def test_agent_output():
    result = analyze_site("construction", "workers without helmets")
    assert isinstance(result, dict)
    assert "top_risks" in result
    assert "recommendations" in result
    assert isinstance(result["top_risks"], list)
    assert isinstance(result["recommendations"], list)
    assert len(result["top_risks"]) > 0
