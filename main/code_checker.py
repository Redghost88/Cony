import os
import subprocess
import sys
import tempfile
from .models import Attempt, Test


def _run_python_file(path: str, stdin: str, timeout: float = 2.0):
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
