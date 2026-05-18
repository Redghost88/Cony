"""
Проверяет код пользователя вне контейнера основной программы
"""

from main.models import Attempt, Test
from main.strategies.code_execution import (
    CodeExecutionStrategy,
    get_execution_strategy,
    resolve_language,
    run_in_docker,
)

__all__ = ["check_attempt", "run_in_docker", "language_for_attempt"]


def language_for_attempt(attempt: Attempt) -> str:
    """Определяет язык выполнения по технологии курса задачи."""
    course = attempt.task.theory.chapter.course
    return resolve_language(course.technology)


def check_attempt(
    attempt: Attempt,
    strategy: CodeExecutionStrategy | None = None,
) -> None:
    """Запускает код попытки по всем тестам задачи, пишет passed и check_log."""
    execution = strategy or get_execution_strategy(language_for_attempt(attempt))
    lines = []
    all_ok = True

    try:
        for t in Test.objects.filter(task=attempt.task):
            t_timeout = 2.0
            res = execution.run(attempt.source_code, t.input_data, timeout=t_timeout)

            out = res["stdout"]
            exp = (t.output_data or "").strip()
            err = res["stderr"]

            if res["timed_out"]:
                lines.append(f"Тест #{t.order}: таймаут")
                all_ok = False
            elif res["exit_code"] != 0:
                lines.append(f"Тест #{t.order}: код выхода {res['exit_code']}")
                if err:
                    lines.append(f"  stderr: {err}")
                all_ok = False
            elif out != exp:
                lines.append(f"Тест #{t.order}: ожидали {exp!r}, получили {out!r}")
                all_ok = False
            else:
                lines.append(f"Тест #{t.order}: OK")
    finally:
        attempt.passed = all_ok
        attempt.check_log = "\n".join(lines)
        attempt.save(update_fields=["passed", "check_log"])
