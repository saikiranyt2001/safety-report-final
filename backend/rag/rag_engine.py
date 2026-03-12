class RAGEngine:
    """
    Simple RAG Engine for retrieving safety regulations
    and generating safety reports.
    """

    def __init__(self):
        # In production this would come from a vector database
        self.regulations = {
            "ppe": "Workers must wear helmets, gloves, and safety shoes.",
            "fire": "Fire extinguishers must be accessible within 15 meters.",
            "electrical": "Electrical panels must be properly insulated.",
            "working_at_height": "Workers above 2 meters must use fall protection."
        }

    def retrieve(self, query: str):
        """
        Retrieve relevant safety regulations based on query
        """

        results = []
        query_lower = query.lower()

        for key, regulation in self.regulations.items():
            if key in query_lower:
                results.append(regulation)

        if not results:
            results.append("Follow general workplace safety regulations.")

        return results

    def generate_report(self, user_request: str):
        """
        Generate a formatted safety report
        """

        regulations = self.retrieve(user_request)

        report = "Safety Report\n"
        report += "====================\n\n"

        report += f"Request:\n{user_request}\n\n"

        report += "Relevant Regulations:\n"
        for r in regulations:
            report += f"- {r}\n"

        report += "\nRecommendations:\n"
        report += "Ensure compliance with the listed safety regulations."

        return report