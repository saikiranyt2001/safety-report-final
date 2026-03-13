from openai import OpenAI
import os
from backend.core.ai_client import chat_completion


def ask_ai(prompt: str):

    return chat_completion(prompt)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_safety_report(hazards, safety_rules):

    prompt = f"""
    You are a safety expert.

    Hazards detected:
    {hazards}

    Safety guidelines:
    {safety_rules}

    Generate a structured safety report including:
    - hazard description
    - risk level
    - mitigation steps
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )

    return response.choices[0].message.content