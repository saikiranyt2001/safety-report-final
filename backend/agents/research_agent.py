class ResearchAgent:

    def research(self, topic: str):
        """
        Perform research on a given topic.
        Returns a simple structured response.
        """

        result = f"Research for {topic}"

        return {
            "status": "success",
            "topic": topic,
            "result": result
        }