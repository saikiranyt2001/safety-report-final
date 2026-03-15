import base64

from backend.core.ai_client import get_openai_client


def analyze_image(image_path):
    client = get_openai_client()
    with open(image_path, "rb") as img:
        base64_image = base64.b64encode(img.read()).decode("utf-8")

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Identify workplace safety hazards in this image."
                    },
                    {
                        "type": "input_image",
                        "image_base64": base64_image
                    }
                ]
            }
        ]
    )

    return response.output_text
