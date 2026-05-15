"""
Асинхронные задачи для Celery
"""

from datetime import datetime

from celery import shared_task
from main.models import Attempt, Course, UserStats
from main.code_checker import check_attempt, run_in_docker
from main.utils import is_yesterday, update_course_progress


@shared_task(bind=True, acks_late=True, max_retries=2, default_retry_delay=5)
def send_attempt(self, attempt_id, course_id):
    """Асинхронно проверяет посылку с кодом пользователя"""
    try:
        attempt = Attempt.objects.get(id=attempt_id)
        attempt.status = "running"
        attempt.save(update_fields=["status"])
        check_attempt(attempt)

        if attempt.passed:
            task = attempt.task
            task.decided = True
            task.save(update_fields=["decided"])

            course = Course.objects.get(id=course_id)
            update_course_progress(course, attempt.user)
            user_stat = UserStats.objects.get(user=attempt.user)
            task_complete_date = user_stat.last_task_complete_date
            if task_complete_date is None or is_yesterday(task_complete_date):
                user_stat.complete_seria += 1
            user_stat.last_task_complete_date = datetime.now().date()
            user_stat.save(update_fields=["last_task_complete_date", "complete_seria"])

        attempt.status = "finished"
        attempt.save(update_fields=["status"])
        return attempt.passed
    except Exception as e:
        attempt.status = "error"
        attempt.save(update_fields="status")
        self.retry(exc=e)


@shared_task(ignore_result=False)
def test_user_code(code: str, stdin: str, timeout: float = 5.0):
    """Асинхронная задача для теста кода пользователем."""
    return run_in_docker(code, stdin, timeout)
