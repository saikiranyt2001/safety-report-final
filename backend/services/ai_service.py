from backend.core.ai_client import chat_completion, get_openai_client


def ask_ai(prompt: str):

    return chat_completion(prompt)

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

    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )

    return response.choices[0].message.content
