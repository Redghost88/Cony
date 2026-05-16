"""
Отвечает за выполнение кода, проверку задач и управление попытками.
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from main.models import Task, Attempt
from main.tasks import send_attempt, test_user_code


@require_http_methods(["POST"])
def run_code(request):
    """
    Выполняет пользовательский Python-код в изолированном Docker-контейнере.

    Принимает код и входные данные, запускает асинхронную задачу Celery
    и ожидает результат выполнения.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'code': str, 'input_data': str}.

    Returns:
        JsonResponse: {'output': str} при успехе или {'error': str} при ошибке.
    """
    request_body = json.loads(request.body)
    code = request_body.get("code")
    input_data = request_body.get("input_data")
    code_timeout = 2
    try:
        async_result = test_user_code.apply_async(
            args=[code, input_data, code_timeout]
        ).get(timeout=code_timeout)

        if async_result["stdout"]:
            output = async_result["stdout"]
        else:
            output = '<div style="color: #dc3545;">' + async_result["stderr"] + "</div>"
        return JsonResponse({"output": output})
    except Exception as e:
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
    code = json.loads(request.body)["source_code"]
    task_id = int(json.loads(request.body)["task_id"])
    task = Task.objects.get(id=task_id)
    attempt = Attempt.objects.create(task=task, user=request.user, source_code=code)
    course_id = json.loads(request.body)["course_id"]
    send_attempt.delay(attempt.id, course_id)

    attempts = Attempt.objects.filter(task=task)
    return JsonResponse({"attempts": list(attempts[:5].values())})


def get_task_attempts(request, task_id):
    """Возвращает все попытки решения пользователем конкретной задачи"""
    task = Task.objects.get(id=task_id)
    attempts = Attempt.objects.filter(task=task)
    return JsonResponse({"attempts": list(attempts[:5].values())})


@require_http_methods(["GET"])
def get_attempt_status(request, attempt_id):
    """Возвращает текущий статус проверки."""
    try:
        attempt = Attempt.objects.only("status", "passed", "check_log").get(
            id=attempt_id
        )
        return JsonResponse(
            {
                "status": attempt.status,
                "passed": attempt.passed,
                "check_log": attempt.check_log,
            }
        )
    except Attempt.DoesNotExist:
        return JsonResponse({"error": "Not found"})
