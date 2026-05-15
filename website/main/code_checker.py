"""
Проверяет код пользователя вне контейнера основной программы
"""

import os
import subprocess
import tempfile
import uuid
from .models import Attempt, Test

LANGS = {
    "python": {"image": "python:3.12-slim", "cmd": ["python", "solution.py"]},
    "cpp": {
        "image": "gcc:12-slim",
        "cmd": ["bash", "-c", "g++ solution.cpp -o sol && ./sol"],
    },
}
MEMORY_LIMIT = "128m"
PIDS_LIMIT = "64"


def run_in_docker(code: str, stdin: str, timeout: float = 2.0):
    """
    Запускает Python-код в изолированном Docker-контейнере.
    Возвращает dict с stdout, stderr, exit_code и флагом timed_out.
    """
    container_name = f"check_{uuid.uuid4().hex[:8]}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        code_path = os.path.join(tmp_dir, "solution.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code)

        cmd = [
            "docker",
            "run",
            "--name",
            container_name,
            "--network=none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,size=64m,mode=755",
            "--memory",
            MEMORY_LIMIT,
            "--pids-limit",
            PIDS_LIMIT,
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--user",
            "1000:1000",
            "--rm",
            "-v",
            f"{tmp_dir}:/app:ro",
            "-w",
            "/app",
            "-i",
            LANGS["python"]["image"],
            *LANGS["python"]["cmd"],
        ]

        try:
            # +1.5 сек буфера на запуск Docker демона
            proc = subprocess.run(
                cmd,
                input=(stdin or "").encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 1.5,
                check=True,
            )
            return {
                "stdout": proc.stdout.decode("utf-8", errors="ignore").strip(),
                "stderr": proc.stderr.decode("utf-8", errors="ignore").strip(),
                "exit_code": proc.returncode,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            # Принудительная остановка зависшего контейнера
            subprocess.run(
                ["docker", "stop", "-t", "1", container_name],
                capture_output=True,
                check=True,
            )
            return {
                "stdout": "",
                "stderr": "Time Limit Exceeded",
                "exit_code": 124,
                "timed_out": True,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Docker error: {str(e)}",
                "exit_code": -1,
                "timed_out": False,
            }
        finally:
            subprocess.run(
                ["docker", "rm", "-f", container_name], capture_output=True, check=True
            )


def check_attempt(attempt: Attempt) -> None:
    """Запускает код попытки по всем тестам задачи, пишет passed и check_log."""
    lines = []
    all_ok = True

    try:
        for t in Test.objects.filter(task=attempt.task):
            t_timeout = 2.0

            res = run_in_docker(attempt.source_code, t.input_data, timeout=t_timeout)

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
