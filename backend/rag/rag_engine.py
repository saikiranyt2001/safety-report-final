import os

from backend.rag.regulation_loader import RegulationLoader
from backend.core.ai_client import chat_completion

def generate_answer(context, question):

    prompt = f"""
    Context:
    {context}

    Question:
    {question}
    """

    return chat_completion(prompt)

class RAGEngine:
    """Simple rule-based RAG over local safety regulations."""

    def __init__(self):
        regulation_path = os.path.join(
            os.path.dirname(__file__),
            "regulations.json",
        )
        self.loader = RegulationLoader(regulation_path)
        self.regulations = self.loader.get_all()

    def _query_terms(self, query: str) -> list[str]:
        query_lower = query.lower().strip()
        terms = [term for term in query_lower.replace("?", "").split() if len(term) > 2]

        # Safety synonyms to improve retrieval hits for real user prompts.
        if "scaffold" in query_lower or "scaffolding" in query_lower:
            terms.extend(["fall", "heights", "protection"])
        if "welding" in query_lower:
            terms.extend(["ppe", "fire", "electrical"])
        if "osha" in query_lower:
            terms.extend(["regulation", "fall", "protection", "ppe"])

        return list(dict.fromkeys(terms))

    def retrieve(self, query: str):
        """Retrieve matching regulations from local JSON knowledge base."""
        terms = self._query_terms(query)
        matches = []

        for regulation in self.regulations:
            haystack = " ".join(
                [
                    str(regulation.get("regulation", "")),
                    str(regulation.get("category", "")),
                    str(regulation.get("reference", "")),
                ]
            ).lower()

            if any(term in haystack for term in terms):
                matches.append(regulation)

        # Keep response concise and relevant.
        return matches[:3]

    def answer_query(self, query: str) -> str:
        """Return a concise safety-advisor style response."""
        query_lower = query.lower()

        if "fall" in query_lower and ("osha" in query_lower or "protection" in query_lower):
            return (
                "Fall protection is required when workers are exposed to heights greater "
                "than 6 feet. Guardrails, safety nets, or personal fall arrest systems "
                "must be used."
            )

        matches = self.retrieve(query)
        if not matches:
            return (
                "Follow core workplace safety principles: complete a risk assessment, "
                "enforce PPE usage, and apply site-specific regulations before work starts."
            )

        lines = []
        for item in matches:
            lines.append(
                f"{item.get('regulation', '')} "
                f"({item.get('category', 'General')}, {item.get('reference', 'Ref N/A')})"
            )

        return "\n".join(lines)

    def generate_report(self, user_request: str):
        """Generate a formatted safety report using retrieved regulations."""
        matches = self.retrieve(user_request)

        report = "Safety Report\n"
        report += "====================\n\n"
        report += f"Request:\n{user_request}\n\n"
        report += "Relevant Regulations:\n"

        if matches:
            for item in matches:
                report += (
                    f"- {item.get('regulation', '')} "
                    f"({item.get('category', 'General')}, {item.get('reference', 'Ref N/A')})\n"
                )
        else:
            report += "- Follow general workplace safety regulations.\n"

        report += "\nRecommendations:\n"
        report += "Ensure compliance with the listed safety regulations."

        return report