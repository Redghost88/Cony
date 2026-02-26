import requests
import json
from cony.settings import OPEN_ROUTER_API_TOKEN
from openai import OpenAI

def chat(massage: str) -> str:
    print("work")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPEN_ROUTER_API_TOKEN,
    )

    # First API call with reasoning
    response = client.chat.completions.create(
        model="stepfun/step-3.5-flash:free",
        messages=[
            {
                "role": "user",
                "content": massage
            }
        ],
    )

    # Extract the assistant message with reasoning_details
    response = response.choices[0].message
    return response.content