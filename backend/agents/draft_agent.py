from backend.risk.risk_matrix import calculate_risk

class DraftAgent:
    def generate_draft_report(self, hazard, likelihood, consequence):
        if not hazard:
            return {"error": "Hazard description required"}
        risk_level = calculate_risk(likelihood, consequence)
        return {
            "hazard": hazard,
            "likelihood": likelihood,
            "consequence": consequence,
            "risk_level": risk_level,
            "recommended_action": "Further mitigation controls should be applied according to WHS guidelines.",
            "status": "draft_generated"
        }
