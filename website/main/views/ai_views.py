"""
Отвечает за генерацию контента и взаимодействие с AI-агентом.
"""

import json
import logging
import re
from django.http import JsonResponse
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods
from main.ai_agent import chat
from main.models import Theory, Task
from main.prompts import (
    CHAT_SETTINGS,
    GENERATE_COURSE,
    STYLE_RULES,
    GENERATE_THEORY,
    GENERATE_TASK,
)
from main.utils import build_task_response

logger = logging.getLogger(__name__)


def generate_theory(chapter_name: str, technology: str, wish="") -> list:
    """
    Генерирует структурированный учебный контент с использованием AI.

    Формирует промпт, отправляет запрос к нейросети и парсит ответ в список словарей.

    Args:
        chapter_name (str): Название учебной темы.
        technology (str): Изучаемая технология (например, 'Python').

    Returns:
        list: Список словарей с ключами 'title' и 'content'.

    Raises:
        json.JSONDecodeError: Если ответ от AI не является валидным JSON.
    """
    logger.info(f"Генерация теории: глава='{chapter_name}', технология='{technology}'")
    prompt = GENERATE_THEORY + STYLE_RULES
    question = (
        prompt
        + "\n Название главы:"
        + chapter_name
        + ", Название технологии:"
        + technology
    )
    if wish:
        question += "Пожелания:" + wish
    try:
        answer = chat(question)
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", answer, re.DOTALL)
        json_str = match.group(1).strip() if match else answer.strip()
        result = json.loads(json_str)
        logger.info(f"Теория сгенерирована успешно: блоков={len(result)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(
            f"Ошибка парсинга JSON при генерации теории: {e}, ответ AI: {answer[:200]}"
        )
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации теории: {e}")
        raise


@require_http_methods(["POST"])
def generate_tasks(request) -> JsonResponse:
    """
    Генерирует практическую задачу и тесты на основе теоретического блока через AI.

    Извлекает ID теории и задачи, удаляет старые тесты, формирует промпт,
    парсит ответ AI и сохраняет новую задачу с тестовыми случаями в БД.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'technology': str, 'theory': int, 'task': int}.

    Returns:
        JsonResponse: Данные новой задачи и списка тестов для фронтенда.
    """
    logger.info(f"Генерация задач запрошена пользователем: {request.user}")
    try:
        request_body = json.loads(request.body)
        technology = request_body.get("technology")
        wish = request_body.get("wish")
        theory = Theory.objects.get(id=int(request_body.get("theory")))
        task = Task.objects.get(id=int(request_body.get("task")))
        logger.info(f"Генерация задачи: задача ID={task.id}")

        question = GENERATE_TASK % (technology, theory.title, strip_tags(theory.text), wish)
        answer = json.loads(chat(question))
        task_info = answer[0]
        tests_info = answer[1]
        task.title = task_info["title"]
        task.task_content = task_info["content"]
        task.input_data = task_info["input_data"]
        task.output_data = task_info["output_data"]
        task.is_generated = True
        task.save()

        logger.info(f"Задача сгенерирована успешно: ID={task.id}")
        return JsonResponse(build_task_response(task, tests_info))
    except Exception as e:
        logger.error(f"Ошибка при генерации задач: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def generate_course(request):
    """
    Генерирует структуру курса на основе пользовательского запроса.

    Args:
        request (HttpRequest): GET-запрос с параметром 'question'.

    Returns:
        JsonResponse: JSON-ответ с полем 'answer', содержащим сгенерированный контент.
    """
    question_text = request.GET.get("question", "")
    logger.info(f"Генерация курса запрошена: вопрос='{question_text[:100]}...'")
    question = GENERATE_COURSE + question_text
    context = {"answer": chat(question)}
    logger.info("Курс сгенерирован успешно")
    return JsonResponse(context)


def generate_chat_answer(request):
    """
    Отвечает на вопрос пользователя в чате, используя системные инструкции AI.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'question': str}.

    Returns:
        JsonResponse: JSON-ответ с полем 'answer'.
    """
    try:
        request_body = json.loads(request.body)
        question_text = request_body.get("question", "")
        logger.info(f"Чат-ответ запрошен: вопрос='{question_text[:100]}...'")
        question = CHAT_SETTINGS + "\n" + question_text
        print(question)
        context = {"answer": chat(question)}
        logger.info("Чат-ответ сгенерирован успешно")
        return JsonResponse(context)
    except Exception as e:
        logger.error(f"Ошибка при генерации чат-ответа: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def generate_answer(request):
    """
    Обрабатывает GET-запрос с параметром ``question``, добавляет системные инструкции
    к запросу и отправляет его в функцию :func:`~core.utils.chat`. Возвращает ответ
    в формате JSON для использования в AJAX-запросах.

    :param request: Объект HTTP-запроса Django.
    :type request: HttpRequest
    :return: JSON-ответ с полем ``answer``, содержащим сгенерированный текст.
    :rtype: JsonResponse

    :query string question: Текст вопроса от пользователя (обязательный параметр).
    :query string: Если параметр ``question`` отсутствует, используется пустая строка.

    """
    question_text = request.GET.get("question", "")
    logger.info(f"Генерация ответа запрошена: вопрос='{question_text[:100]}...'")
    question = STYLE_RULES + question_text
    context = {"answer": chat(question)}
    logger.info("Ответ сгенерирован успешно")
    return JsonResponse(context)
