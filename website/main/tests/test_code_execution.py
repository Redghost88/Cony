"""Тесты стратегий запуска кода."""

from main.strategies.code_execution import (
    get_execution_strategy,
    resolve_language,
)


class TestResolveLanguage:
    def test_python_variants(self):
        assert resolve_language("Python") == "python"
        assert resolve_language("python3") == "python"

    def test_cpp_variants(self):
        assert resolve_language("C++") == "cpp"
        assert resolve_language("cpp") == "cpp"

    def test_unknown_defaults_to_python(self):
        assert resolve_language("") == "python"
        assert resolve_language("JavaScript") == "python"


class TestGetExecutionStrategy:
    def test_python_strategy(self):
        strategy = get_execution_strategy("python")
        assert strategy.lang_id == "python"

    def test_cpp_strategy(self):
        strategy = get_execution_strategy("C++")
        assert strategy.lang_id == "cpp"

    def test_unknown_technology_uses_python_strategy(self):
        strategy = get_execution_strategy("rust")
        assert strategy.lang_id == "python"
