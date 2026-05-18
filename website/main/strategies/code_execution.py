"""
Стратегии запуска пользовательского кода в Docker для разных языков.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from typing import TypedDict

MEMORY_LIMIT = "128m"
PIDS_LIMIT = "64"
DOCKER_STARTUP_BUFFER = 1.5


class RunResult(TypedDict):
    """Результат выполнения пользовательского кода в контейнере."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


@dataclass(frozen=True)
class DockerLangConfig:
    """Параметры Docker-образа и команды запуска для одного языка."""

    lang_id: str
    filename: str
    image: str
    cmd: tuple[str, ...]


class CodeExecutionStrategy:
    """Стратегия запуска кода в изолированном Docker-контейнере."""

    def __init__(self, config: DockerLangConfig) -> None:
        """Создаёт стратегию с конфигурацией выбранного языка."""
        self._config = config

    @property
    def lang_id(self) -> str:
        """Идентификатор языка (python, cpp и т.д.)."""
        return self._config.lang_id

    def run(self, code: str, stdin: str, timeout: float = 2.0) -> RunResult:
        """Запускает код в Docker и возвращает stdout, stderr и код выхода."""
        return _run_in_docker(self._config, code, stdin, timeout)


_PYTHON = DockerLangConfig(
    lang_id="python",
    filename="solution.py",
    image="python:3.12-slim",
    cmd=("python", "solution.py"),
)

_CPP = DockerLangConfig(
    lang_id="cpp",
    filename="solution.cpp",
    image="gcc:12-slim",
    cmd=("bash", "-c", "g++ solution.cpp -o sol && ./sol"),
)

_STRATEGIES: dict[str, CodeExecutionStrategy] = {
    "python": CodeExecutionStrategy(_PYTHON),
    "cpp": CodeExecutionStrategy(_CPP),
}

_TECHNOLOGY_ALIASES: dict[str, str] = {
    "python": "python",
    "python3": "python",
    "питон": "python",
    "c++": "cpp",
    "cpp": "cpp",
    "c plus plus": "cpp",
    "с++": "cpp",
}


def resolve_language(technology: str = "") -> str:
    """Сопоставляет название технологии курса с идентификатором стратегии."""
    key = (technology or "").strip().lower()
    if key in _STRATEGIES:
        return key
    return _TECHNOLOGY_ALIASES.get(key, "python")


def get_execution_strategy(lang: str) -> CodeExecutionStrategy:
    """Возвращает стратегию выполнения для указанного языка или технологии."""
    lang_id = resolve_language(lang)
    try:
        return _STRATEGIES[lang_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported language: {lang}") from exc


def run_in_docker(
    code: str,
    stdin: str,
    timeout: float = 2.0,
    lang: str = "python",
) -> RunResult:
    """Запускает код через стратегию выбранного языка."""
    return get_execution_strategy(lang).run(code, stdin, timeout)


def _write_solution_file(directory: str, filename: str, code: str) -> None:
    """Записывает исходный код во временный каталог для монтирования в контейнер."""
    code_path = os.path.join(directory, filename)
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)


def _build_docker_run_command(
    config: DockerLangConfig,
    host_dir: str,
    container_name: str,
) -> list[str]:
    """Формирует команду docker run с ограничениями безопасности и ресурсов."""
    return [
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
        f"{host_dir}:/app:ro",
        "-w",
        "/app",
        "-i",
        config.image,
        *config.cmd,
    ]


def _success_result(proc: subprocess.CompletedProcess[bytes]) -> RunResult:
    """Преобразует успешный завершённый процесс Docker в RunResult."""
    return {
        "stdout": proc.stdout.decode("utf-8", errors="ignore").strip(),
        "stderr": proc.stderr.decode("utf-8", errors="ignore").strip(),
        "exit_code": proc.returncode,
        "timed_out": False,
    }


def _stop_container(container_name: str) -> None:
    """Принудительно останавливает контейнер при превышении лимита времени."""
    subprocess.run(
        ["docker", "stop", "-t", "1", container_name],
        capture_output=True,
        check=True,
    )


def _remove_container(container_name: str) -> None:
    """Удаляет контейнер, если он ещё существует."""
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        check=True,
    )


def _execute_container(
    cmd: list[str],
    stdin: str,
    timeout: float,
    container_name: str,
) -> RunResult:
    """Запускает контейнер и обрабатывает успех, таймаут или ошибку Docker."""
    try:
        proc = subprocess.run(
            cmd,
            input=(stdin or "").encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + DOCKER_STARTUP_BUFFER,
            check=True,
        )
        return _success_result(proc)
    except subprocess.TimeoutExpired:
        _stop_container(container_name)
        return {
            "stdout": "",
            "stderr": "Time Limit Exceeded",
            "exit_code": 124,
            "timed_out": True,
        }
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {
            "stdout": "",
            "stderr": f"Docker error: {exc}",
            "exit_code": -1,
            "timed_out": False,
        }
    finally:
        _remove_container(container_name)


def _run_in_docker(
    config: DockerLangConfig,
    code: str,
    stdin: str,
    timeout: float,
) -> RunResult:
    """Запускает пользовательский код в Docker по конфигурации языка."""
    container_name = f"check_{uuid.uuid4().hex[:8]}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        _write_solution_file(tmp_dir, config.filename, code)
        cmd = _build_docker_run_command(config, tmp_dir, container_name)
        return _execute_container(cmd, stdin, timeout, container_name)
