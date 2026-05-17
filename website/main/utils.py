"""
Вспомогательные функции для работы программы
"""

from datetime import datetime, timedelta
import logging

from main.models import Chapter, Test, Theory, Task

logger = logging.getLogger(__name__)


def is_yesterday(date):
    """Проверяет, была ли дата вчера"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    return date.date() == yesterday


def update_course_progress(course, user) -> None:
    """
    Рассчитывает и обновляет общий прогресс пользователя по конкретному курсу.

    Аргументы:
        course (Course): Экземпляр модели курса, для которого считается прогресс.
        user (User): Экземпляр модели пользователя, чей прогресс анализируется.

    Логика расчета:
        1. Прогресс курса складывается из прогресса каждой его главы (Chapter).
        2. Вес каждой главы в курсе равнозначен: 1 / количество_глав.
        3. Прогресс главы определяется как доля решенных задач (Task.decided=True),
           привязанных к блокам теории (Theory) этой главы.
        4. Если задача по конкретной теории решена, к прогрессу главы добавляется
           значение: 1 / количество_блоков_теории_в_главе.
        5. Финальный результат переводится в проценты (0-100) и округляется.

    Действие:
        Обновляет поле 'progress' в объекте 'course' и сохраняет его в базе данных.

    Возвращает:
        None
    """
    progress = 0
    chapters = Chapter.objects.filter(course=course)
    for c in chapters:
        chapter_progress = 0.0
        theory_blocks = Theory.objects.filter(chapter=c)
        for t in theory_blocks:
            if Task.objects.filter(theory=t, user=user).exists():
                task = Task.objects.get(theory=t, user=user)
                if task.decided:
                    chapter_progress += 1 / len(theory_blocks)
        progress += chapter_progress / len(chapters)
    course.progress = round(progress * 100)
    course.save(update_fields=["progress"])


def clean_duplicate_theories(chapter, task_id):
    """Удаляет дупликаты блоков теории"""
    theory_blocks = Theory.objects.filter(chapter=chapter)
    for _ in range(len(theory_blocks)):
        theory_same_order = Theory.objects.filter(chapter=chapter, order=task_id)
        if len(theory_same_order) > 1:
            for t in theory_same_order[1:]:
                t.delete()


def create_new_tests(task, tests_info: list) -> list:
    """Создает объекты Test для задачи"""
    if task.is_generated:
        Test.objects.filter(task=task).delete()
        logger.debug(f"Удалены старые тесты для задачи ID={task.id}")
    tests = []
    for i in range(len(tests_info)):
        test = Test.objects.create(
            task=task,
            input_data=tests_info[i][0],
            output_data=tests_info[i][1],
            order=i,
        )
        tests.append({"input_data": test.input_data, "output_data": test.output_data})
    return tests


def build_task_response(task, tests_info) -> dict:
    """Формирует JSON-ответ для фронтенда задачи"""
    response = {
        "task_title": task.title,
        "task_text": task.task_content,
        "input_data": task.input_data,
        "output_data": task.output_data,
        "tests": create_new_tests(task, tests_info),
    }
    return response
