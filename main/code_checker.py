import os
import subprocess
import sys
import tempfile

from django.db.models import Model

from .models import Attempt, Test


def _run_python_file(path: str, stdin: str, timeout: float = 2.0):
    """
        Запускает указанный Python-файл как отдельный процесс и передает данные в стандартный ввод.

        Аргументы:
            path (str): Абсолютный или относительный путь к исполняемому .py файлу.
            stdin (str): Строка данных, которая будет передана в программу пользователя
                как входной поток (стандартный ввод).
            timeout (float, optional): Максимальное время выполнения файла в секундах.
                По умолчанию — 2.0 секунды.

        Логика работы:
            1. Использует текущий интерпретатор Python (sys.executable) для запуска файла.
            2. Передает содержимое 'stdin' в процесс.
            3. Перехватывает вывод (stdout) и ошибки (stderr) благодаря 'capture_output=True'.
            4. Работает в текстовом режиме (text=True), что позволяет получать строки вместо байтов.

        Возвращает:
            subprocess.CompletedProcess: Объект с результатами выполнения, включая
                поля .stdout (вывод), .stderr (ошибки) и .returncode (код возврата).

        Исключения:
            subprocess.TimeoutExpired: Выбрасывается, если время выполнения превышает лимит 'timeout'.
            FileNotFoundError: Выбрасывается, если файл по пути 'path' не найден.
        """
    return subprocess.run(
        [sys.executable, path],
        input=stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def check_attempt(attempt: Attempt) -> None:
    """Запускает код попытки по всем тестам задачи, пишет passed и check_log."""
    lines = []
    all_ok = True

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(attempt.source_code)
        path = f.name

    try:
        for t in Test.objects.filter(task=attempt.task):
            try:
                r = _run_python_file(path, t.input_data)
            except subprocess.TimeoutExpired:
                lines.append(f"Тест #{t.order}: таймаут")
                all_ok = False
                continue

            out = (r.stdout or "").strip()
            exp = (t.output_data or "").strip()
            err = (r.stderr or "").strip()

            if r.returncode != 0:
                lines.append(f"Тест #{t.order}: код выхода {r.returncode}")
                if err:
                    lines.append(f"  stderr: {err}")
                all_ok = False
                continue

            if out != exp:
                lines.append(f"Тест #{t.order}: ожидали {exp!r}, получили {out!r}")
                all_ok = False
            else:
                lines.append(f"Тест #{t.order}: OK")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    attempt.passed = all_ok
    attempt.check_log = "\n".join(lines)
    attempt.save(update_fields=["passed", "check_log"])
