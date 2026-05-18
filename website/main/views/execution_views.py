"""
Отвечает за выполнение кода, проверку задач и управление попытками.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from main.models import Task, Attempt
from main.strategies.code_execution import resolve_language
from main.tasks import send_attempt, test_user_code

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def run_code(request):
    """
    Выполняет пользовательский код в изолированном Docker-контейнере.

    Принимает код и входные данные, запускает асинхронную задачу Celery
    и ожидает результат выполнения.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'code': str, 'input_data': str, 'language': str}.

    Returns:
        JsonResponse: {'output': str} при успехе или {'error': str} при ошибке.
    """
    logger.info(f"Выполнение кода запрошено пользователем: {request.user}")
    try:
        request_body = json.loads(request.body)
        code = request_body.get("code")
        input_data = request_body.get("input_data")
        language = resolve_language(request_body.get("language", "python"))
        code_timeout = 2
        logger.debug(
            f"Выполнение кода: язык={language}, длина кода={len(code)}, "
            f"входные данные='{input_data[:100] if input_data else 'нет'}'"
        )

        async_result = test_user_code.apply_async(
            args=[code, input_data, code_timeout, language]
        ).get(timeout=code_timeout)

        if async_result["stdout"]:
            output = async_result["stdout"]
            logger.info(f"Код выполнен успешно: вывод='{output[:100]}...'")
        else:
            output = '<div style="color: #dc3545;">' + async_result["stderr"] + "</div>"
            logger.warning(
                f"Ошибка выполнения кода: ошибка='{async_result['stderr'][:200]}'"
            )
        return JsonResponse({"output": output})
    except Exception as e:
        logger.error(f"Исключение при выполнении кода: {e}")
        return JsonResponse({"error": str(e)})


@require_http_methods(["POST"])
def check_code(request):
    """
    Создаёт попытку решения задачи и запускает её асинхронную проверку.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'source_code': str, 'task_id': int, 'course_id': int}.

    Returns:
        JsonResponse: Список последних 5 попыток пользователя.
    """
    logger.info(f"Проверка кода запрошена пользователем: {request.user}")
    try:
        data = json.loads(request.body)
        code = data["source_code"]
        task_id = int(data["task_id"])
        task = Task.objects.get(id=task_id)
        attempt = Attempt.objects.create(task=task, user=request.user, source_code=code)
        course_id = data["course_id"]
        send_attempt.delay(attempt.id, course_id)

        attempts = Attempt.objects.filter(task=task)
        logger.info(
            f"Попытка создана: ID={attempt.id}, задача={task_id}, курс={course_id}, длина кода={len(code)}"
        )
        return JsonResponse({"attempts": list(attempts[:5].values())})
    except Exception as e:
        logger.error(f"Ошибка при создании попытки: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def get_task_attempts(request, task_id):
    """Возвращает все попытки решения пользователем конкретной задачи"""
    logger.info(f"Запрос попыток задачи: задача={task_id}, пользователь={request.user}")
    task = Task.objects.get(id=task_id)
    attempts = Attempt.objects.filter(task=task)
    logger.info(f"Возвращено попыток: {attempts.count()} для задачи={task_id}")
    return JsonResponse({"attempts": list(attempts[:5].values())})


@require_http_methods(["GET"])
def get_attempt_status(request, attempt_id):
    """Возвращает текущий статус проверки."""
    logger.info(f"Запрос статуса попытки: ID={attempt_id}, пользователь={request.user}")
    try:
        attempt = Attempt.objects.only("status", "passed", "check_log").get(
            id=attempt_id
        )
        logger.info(
            f"Статус попытки: ID={attempt_id}, статус={attempt.status}, пройдено={attempt.passed}"
        )
        return JsonResponse(
            {
                "status": attempt.status,
                "passed": attempt.passed,
                "check_log": attempt.check_log,
            }
        )
    except Attempt.DoesNotExist:
        logger.error(f"Попытка не найдена: ID={attempt_id}")
        return JsonResponse({"error": "Not found"})
