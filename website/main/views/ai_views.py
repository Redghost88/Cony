"""
Отвечает за генерацию контента и взаимодействие с AI-агентом.
"""
import json
from django.http import JsonResponse
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods
from main.ai_agent import chat
from main.models import Theory, Task, Test
from main.prompts import (
    CHAT_SETTINGS,
    GENERATE_COURSE,
    STYLE_RULES,
    GENERATE_THEORY,
    GENERATE_TASK,
)


def generate_theory(chapter_name: str, technology: str) -> list:
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
    prompt = GENERATE_THEORY + STYLE_RULES
    question = (
        prompt
        + "\n Название главы:"
        + chapter_name
        + ", Название технологии:"
        + technology
    )
    answer = chat(question)
    return json.loads(answer)


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
    request_body = json.loads(request.body)
    technology = request_body.get("technology")
    theory = Theory.objects.get(id=int(request_body.get("theory")))
    task = Task.objects.get(id=int(request_body.get("task")))

    if task.is_generated:
        Test.objects.filter(task=task).delete()

    question = GENERATE_TASK % (technology, theory.title, strip_tags(theory.text))
    answer = json.loads(chat(question))
    task_info = answer[0]
    tests_info = answer[1]
    task.title = task_info["title"]
    task.task_content = task_info["content"]
    task.input_data = task_info["input_data"]
    task.output_data = task_info["output_data"]
    task.is_generated = True
    task.save()
    response = {
        "task_title": task.title,
        "task_text": task.task_content,
        "input_data": task.input_data,
        "output_data": task.output_data,
        "tests": [],
    }
    tests = []
    for i in range(len(tests_info)):
        test = Test.objects.create(
            task=task,
            input_data=tests_info[i][0],
            output_data=tests_info[i][1],
            order=i,
        )
        tests.append({"input_data": test.input_data, "output_data": test.output_data})
    response["tests"] = tests

    return JsonResponse(response)


def generate_course(request):
    """
    Генерирует структуру курса на основе пользовательского запроса.

    Args:
        request (HttpRequest): GET-запрос с параметром 'question'.

    Returns:
        JsonResponse: JSON-ответ с полем 'answer', содержащим сгенерированный контент.
    """
    question = GENERATE_COURSE + request.GET.get("question", "")
    context = {"answer": chat(question)}
    return JsonResponse(context)


def generate_chat_answer(request):
    """
    Отвечает на вопрос пользователя в чате, используя системные инструкции AI.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'question': str}.

    Returns:
        JsonResponse: JSON-ответ с полем 'answer'.
    """
    request_body = json.loads(request.body)
    question = CHAT_SETTINGS + "\n" + request_body.get("question", "")
    print(question)
    context = {"answer": chat(question)}
    return JsonResponse(context)


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
    question = STYLE_RULES + request.GET.get("question", "")
    context = {"answer": chat(question)}
    return JsonResponse(context)
