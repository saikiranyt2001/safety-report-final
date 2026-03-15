import os

from openai import OpenAI


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


def get_openai_client() -> OpenAI:
    return _get_client()


def chat_completion(prompt, max_tokens=400):
    client = _get_client()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens
    )

    return response.choices[0].message.content
