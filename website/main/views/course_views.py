"""
Отвечает за отображение курсов, глав и навигацию по обучению.
"""

import json
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from main.models import Chapter, Course, Theory, Task, Test, Attempt
from main.utils import clean_duplicate_theories, update_course_progress
from .ai_views import generate_theory

logger = logging.getLogger(__name__)


def home(request):
    """
    Отображает главную страницу приложения.

    Обрабатывает GET-запрос и возвращает отрендеренный шаблон главной страницы.

    :param request: Объект HTTP-запроса Django.
    :type request: HttpRequest
    :return: Объект HttpResponse с отрендеренным шаблоном 'index.html'.
    :rtype: HttpResponse
    """
    logger.info(f"Главная страница запрошена пользователем: {request.user}")
    courses = []
    for course in Course.objects.all():
        courses.append([course, course.current_chapter_number, 0])

    context = {"courses": courses}
    logger.info(f"Главная страница отображена, курсов: {len(courses)}")
    return render(request, "index.html", context)


@login_required
def create_course(request):
    """
    Отображает страницу создания нового курса.

    Обрабатывает GET-запрос и возвращает отрендеренный шаблон формы создания курса.
    При обработке POST-запроса (добавляется при реализации логики) выполняет валидацию
    данных и создаёт новый объект :class:`~courses.models.Course`.

    :param request: Объект HTTP-запроса Django.
    :type request: HttpRequest
    :return: Объект HttpResponse с отрендеренным шаблоном 'create_course.html'.
    :rtype: HttpResponse
    """
    logger.info(f"Создание курса запрошено пользователем: {request.user}")
    if request.method == "POST":

        course = Course.objects.create(
            author=request.user,
            title=request.POST.get("course_title"),
            technology=request.POST.get("technology"),
        )

        course.create_chapters(request.POST.getlist("chapter_name"))
        chapter1 = Chapter.objects.get(course=course, order=0)
        theory_blocks = generate_theory(chapter1.title, course.technology)
        chapter1.create_theories(theory_blocks)

        logger.info(
            f"Курс создан: ID={course.id}, название='{course.title}', автор={request.user}"
        )
        return redirect("home")
    context = {}
    logger.info("Отображена форма создания курса")
    return render(request, "create_course.html", context)


@login_required
def course_page(request, course_id, chapter_id, theory_id):
    """Отображает страницу урока: теорию, задачу, тесты и историю попыток."""
    logger.info(
        f"Страница курса запрошена: курс={course_id}, глава={chapter_id}, теория={theory_id}"
    )
    course = get_object_or_404(Course, id=course_id)
    course.current_chapter_number = chapter_id
    course.save(update_fields=["current_chapter_number"])

    chapters = Chapter.objects.filter(course=course).order_by("order")
    chapter = Chapter.objects.get(course=course, order=chapter_id)
    chapter.current_theory_number = theory_id
    chapter.save(update_fields=["current_theory_number"])

    clean_duplicate_theories(chapter, theory_id)

    theory = None
    theory_blocks = Theory.objects.filter(chapter=chapter)
    if theory_blocks:
        theory = Theory.objects.get(chapter=chapter, order=theory_id)

    task, tests, attempts, last_attempt = _get_lesson_data(theory, request.user)

    update_course_progress(course, request.user)
    context = {
        "course": course,
        "chapters": chapters,
        "chapter": chapter,
        "theory_blocks": theory_blocks,
        "theory": theory,
        "task": task,
        "tests": tests,
        "attempts": attempts,
        "last_attempt": last_attempt,
    }
    logger.info(
        f"Страница курса отображена: курс='{course.title}', глав={len(chapters)}, теорий={len(theory_blocks)}"
    )
    return render(request, "course_page.html", context)


def _get_lesson_data(theory, user):
    """Получает задачу, тесты и попытки для текущей теории"""
    task = None
    tests = None
    attempts = []
    last_attempt = None

    if theory:
        try:
            task = Task.objects.get(user=user, theory=theory)
            tests = Test.objects.filter(task=task)
        except ObjectDoesNotExist:
            task = Task.objects.create(theory=theory, user=user)
            logger.debug(f"Создана новая задача: ID={task.id}, теория={theory.id}")

    if task:
        try:
            attempts = Attempt.objects.filter(task=task)
            last_attempt = attempts.first()
            attempts = json.dumps(list(attempts[:5].values()), default=str)
        except ObjectDoesNotExist:
            attempts = []

    return task, tests, attempts, last_attempt


@require_http_methods(["POST"])
def add_new_theory(request):
    """
    Генерирует и сохраняет новые блоки теории для конкретной главы курса.

    Аргументы:
        request (HttpRequest): Объект запроса, содержащий POST-параметры:
            - chapter (int): ID главы, для которой создается теория.
            - course (int): ID курса, к которому относится глава.

    Логика работы:
        1. Извлекает объекты главы и курса из базы данных.
        2. Вызывает внешнюю функцию 'generate_theory' (предположительно ИИ-генератор),
           которая возвращает список словарей с заголовками и контентом.
        3. Создает блоки теории для главы
        4. Перенаправляет пользователя на страницу первой созданной задачи курса.

    Возвращает:
        HttpResponseRedirect: Редирект на 'course_page' для просмотра созданного контента.
    """
    logger.info(f"Добавление новой теории запрошено пользователем: {request.user}")
    chapter_id = int(request.POST.get("chapter"))
    course_id = int(request.POST.get("course"))
    chapter = Chapter.objects.get(id=chapter_id)
    course = Course.objects.get(id=course_id)
    logger.info(
        f"Добавление теории: глава ID={chapter_id} '{chapter.title}', курс ID={course_id} '{course.title}'"
    )

    theory_blocks = generate_theory(chapter.title, course.technology)
    chapter.create_theories(theory_blocks)

    logger.info(f"Теория добавлена: блоков={len(theory_blocks)}, глава={chapter.title}")
    return redirect(
        "course_page",
        course_id=course_id,
        chapter_id=chapter.order,
        theory_id=chapter.current_theory_number,
    )
