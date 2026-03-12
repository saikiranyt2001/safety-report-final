from backend.agents.risk_agent import calculate_risk


class DraftAgent:
    """
    Draft Agent
    Generates a preliminary safety report draft based on hazard input.
    """

    def generate_draft_report(self, hazard: str, likelihood: int, consequence: int):

        # Validate hazard
        if not hazard or hazard.strip() == "":
            return {"status": "error", "message": "Hazard description required"}

        # Validate likelihood and consequence
        if likelihood < 1 or consequence < 1:
            return {
                "status": "error",
                "message": "Likelihood and consequence must be positive numbers"
            }

        # Calculate risk level
        risk_level = calculate_risk(likelihood, consequence)

        # Generate draft safety report
        draft_report = {
            "hazard": hazard,
            "likelihood": likelihood,
            "consequence": consequence,
            "risk_level": risk_level,
            "recommended_action": (
                "Apply additional mitigation controls according to WHS safety guidelines."
            ),
            "status": "draft_generated"
        }

        return draft_report