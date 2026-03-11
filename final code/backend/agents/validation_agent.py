class ValidationAgent:
    def validate(self, report_text: str):
        """
        Basic validation for safety report
        """
        if not report_text:
            return {"status": "error", "message": "Report is empty"}

        return {
            "status": "success",
            "message": "Report validation passed"
        }
