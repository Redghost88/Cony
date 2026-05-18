"""Публичный API стратегий выполнения пользовательского кода."""

from main.strategies.code_execution import (
    CodeExecutionStrategy,
    RunResult,
    get_execution_strategy,
    resolve_language,
    run_in_docker,
)

__all__ = [
    "CodeExecutionStrategy",
    "RunResult",
    "get_execution_strategy",
    "resolve_language",
    "run_in_docker",
]
