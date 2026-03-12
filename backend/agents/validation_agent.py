class ValidationAgent:
    """
    Validation Agent
    Validates generated safety reports before exporting or storing.
    """

    def validate(self, report_text: str):
        """
        Basic validation for safety report
        """

        # Check if report exists
        if not report_text or report_text.strip() == "":
            return {
                "status": "error",
                "message": "Report is empty"
            }

        # Check minimum length (basic quality check)
        if len(report_text) < 20:
            return {
                "status": "warning",
                "message": "Report is too short"
            }

        return {
            "status": "success",
            "message": "Report validation passed"
        }