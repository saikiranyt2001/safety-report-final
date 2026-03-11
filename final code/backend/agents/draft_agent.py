from backend.agents.risk_agent import calculate_risk


class DraftAgent:

    def generate_draft_report(self, hazard: str, likelihood: int, consequence: int):

        # Validate hazard
        if not hazard or hazard.strip() == "":
            return {"error": "Hazard description required"}

        # Validate numbers
        if likelihood < 1 or consequence < 1:
            return {"error": "Likelihood and consequence must be positive numbers"}

        # Calculate risk
        risk_level = calculate_risk(likelihood, consequence)

        # Generate draft report
        draft_report = {
            "hazard": hazard,
            "likelihood": likelihood,
            "consequence": consequence,
            "risk_level": risk_level,
            "recommended_action": "Further mitigation controls should be applied according to WHS guidelines.",
            "status": "draft_generated"
        }

        return draft_report