import requests
import json
from openai import OpenAI
from cony.settings import OPEN_ROUTER_API_TOKEN


def chat(massage: str) -> str:
    """
    Отправляет запрос к AI-модели через OpenRouter API и возвращает ответ.

    Инициализирует клиент OpenAI с базовым URL OpenRouter, отправляет сообщение
    модели ``stepfun/step-3.5-flash:free`` и возвращает сгенерированный контент.

    :param massage: Текст запроса пользователя.
    :type massage: str
    :return: Ответ от AI-модели в виде строки.
    :rtype: str
    """

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPEN_ROUTER_API_TOKEN,
    )

    # First API call with reasoning
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b:free",
        messages=[{"role": "user", "content": massage}],
    )

    # Extract the assistant message with reasoning_details
    response = response.choices[0].message
    return response.content
