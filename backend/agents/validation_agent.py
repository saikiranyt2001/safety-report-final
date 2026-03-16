import os
import re

from backend.core.ai_client import chat_completion


class ValidationAgent:
    """
    Validation Agent
    Validates generated safety reports before exporting or storing.
    """

    def __init__(self, hazard_list=None, regulation_list=None):
        self.hazard_list = hazard_list or []
        self.regulation_list = regulation_list or []

    def _fallback_issues(self, report_text: str):
        text = report_text.strip()
        lowered = text.lower()
        issues = []

        if not text:
            return ["Report is empty."]

        if len(text) < 80:
            issues.append("Report is too short and needs more operational detail.")

        if not re.search(r"\b(ppe|helmet|gloves|goggles|boots|vest)\b", lowered):
            issues.append("PPE requirements or observations are missing.")

        if not re.search(r"\b(location|area|site|zone|floor|warehouse)\b", lowered):
            issues.append("Incident location is not clearly specified.")

        if not re.search(r"\b(action|control|mitigation|corrective|preventive)\b", lowered):
            issues.append("Corrective or preventive actions are not clearly documented.")

        missing_hazards = [
            hazard for hazard in self.hazard_list
            if hazard and hazard.lower() in lowered
        ]
        if self.hazard_list and not missing_hazards:
            issues.append("The report does not clearly reference the expected hazard categories.")

        missing_regulations = [
            rule for rule in self.regulation_list
            if rule and rule.lower() in lowered
        ]
        if self.regulation_list and not missing_regulations:
            issues.append("No regulation or compliance references were found in the report.")

        if not issues:
            issues.append("No major validation issues detected.")

        return issues

    def _ai_issues(self, report_text: str):
        if not os.getenv("OPENAI_API_KEY"):
            return None

        prompt = (
            "You are a workplace safety report validator. Review the report and return up to 5 concise issues. "
            "Focus on missing details, unclear hazards, missing PPE, weak controls, and compliance gaps. "
            "If the report looks good, return exactly: No major validation issues detected.\n\n"
            f"Expected hazards: {', '.join(self.hazard_list) or 'Not specified'}\n"
            f"Expected regulations: {', '.join(self.regulation_list) or 'Not specified'}\n\n"
            f"Report:\n{report_text}"
        )

        try:
            response = chat_completion(prompt, max_tokens=220)
        except Exception:
            return None

        lines = [
            line.strip(" -•\t")
            for line in response.splitlines()
            if line.strip()
        ]
        cleaned = [line for line in lines if len(line) > 3]
        return cleaned[:5] if cleaned else None

    def validate_report(self, report_text: str):
        ai_issues = self._ai_issues(report_text)
        if ai_issues:
            return ai_issues
        return self._fallback_issues(report_text)
