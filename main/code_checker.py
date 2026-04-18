import os
import subprocess
import sys
import tempfile

from django.db.models import Model

from .models import Attempt, Test


def _run_python_file(path: str, stdin: str, timeout: float = 2.0):
    """
    Запускает указанный Python-скрипт с заданным стандартным вводом и захватывает вывод.

    Внутренняя утилита для выполнения внешних Python-файлов через текущий интерпретатор.
    Передаёт ``stdin`` в стандартный ввод процесса, захватывает stdout/stderr и ожидает
    завершения не дольше ``timeout`` секунд. Возвращает объект с результатами выполнения.

    :param path: Абсолютный или относительный путь к Python-скрипту.
    :type path: str
    :param stdin: Строка, передаваемая в стандартный ввод запускаемого скрипта.
    :type stdin: str
    :param timeout: Максимальное время выполнения в секундах. По умолчанию 2.0.
    :type timeout: float
    :return: Объект, содержащий код возврата, stdout и stderr процесса.
    :rtype: subprocess.CompletedProcess
    :raises subprocess.TimeoutExpired: Если выполнение превышает ``timeout``.
    :raises FileNotFoundError: Если файл по указанному ``path`` не найден.
    """
    return subprocess.run(
        [sys.executable, path],
        input=stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def check_attempt(attempt: Attempt) -> None:
    """
    Выполняет автоматическую проверку исходного кода пользователя по всем тестам задачи.

    Сохраняет код во временный файл, последовательно запускает его через вспомогательную
    функцию ``_run_python_file`` с входными данными каждого теста, сравнивает фактический вывод
    с ожидаемым и обновляет статус попытки в базе данных.

    :param attempt: Экземпляр модели ``Attempt``, содержащий проверяемый исходный код.
    :type attempt: Attempt

    :returns: ``None``. Результат проверки записывается непосредственно в объект ``attempt``
              и сохраняется в БД.
    :rtype: None

    **Этапы выполнения:**
      1. Код из ``attempt.source_code`` записывается во временный файл с расширением ``.py``.
      2. Перебираются все тесты, привязанные к ``attempt.task`` (сортировка по ``order``, ``id``).
      3. Для каждого теста запускается файл; анализируются ``stdout``, ``stderr`` и код возврата.
      4. Формируется текстовый лог (``check_log``) и вычисляется общий флаг успешности (``passed``).
      5. Временный файл гарантированно удаляется в блоке ``finally``.
      6. В БД обновляются только поля ``passed`` и ``check_log``.

    :raises OSError: При ошибке создания или удаления временного файла.
    :raises django.db.DatabaseError: При неудачном сохранении обновлённого объекта ``attempt``.
    :raises Exception: Любые непредвиденные ошибки из ``_run_python_file`` или среды выполнения,
                       если они не обработаны внутри вспомогательной функции.

    .. warning::
       Функция выполняет произвольный пользовательский код на сервере.
       Убедитесь, что ``_run_python_file`` работает в изолированной среде (sandbox/Docker)
       с жёсткими ограничениями на время выполнения (timeout), память (memory limit)
       и системные вызовы, чтобы предотвратить уязвимости RCE или атаки типа DoS.

    .. note::
       Для сохранения используется ``update_fields=['passed', 'check_log']``.
       Это предотвращает перезапись других полей модели при конкурентных запросах,
       снижает нагрузку на БД и исключает гонки состояний (race conditions).
    """
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
