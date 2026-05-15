"""
Вспомогательные функции для работы программы
"""

from datetime import datetime, timedelta

from main.models import Chapter, Theory, Task


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
