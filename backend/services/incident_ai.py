from backend.core.ai_client import chat_completion


def generate_incident_report(hazards: list[str], risk_level: str = "UNKNOWN"):
    prompt = f"""
Generate an industrial safety incident report.

Detected hazards: {", ".join(hazards) if hazards else "None"}
Risk level: {risk_level}

Include:
- description
- risk level
- recommended actions
"""

    try:
        return chat_completion(prompt, max_tokens=500)
    except Exception as exc:
        return f"Incident report generation failed: {exc}"