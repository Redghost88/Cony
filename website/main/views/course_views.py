"""
Отвечает за отображение курсов, глав и навигацию по обучению.
"""
import json
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from main.models import Chapter, Course, Theory, Task, Test, Attempt
from main.utils import clean_duplicate_theories, update_course_progress
from .ai_views import generate_theory


def home(request):
    """
    Отображает главную страницу приложения.

    Обрабатывает GET-запрос и возвращает отрендеренный шаблон главной страницы.

    :param request: Объект HTTP-запроса Django.
    :type request: HttpRequest
    :return: Объект HttpResponse с отрендеренным шаблоном 'index.html'.
    :rtype: HttpResponse
    """
    courses = []
    for course in Course.objects.all():
        courses.append(
            [
                course,
                course.current_chapter_number,
                Chapter.objects.get(
                    course=course, order=course.current_chapter_number
                ).current_theory_number,
            ]
        )

    context = {"courses": courses}
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
    if request.method == "POST":
        chapters = request.POST.getlist("chapter_name")
        course_title = request.POST.get("course_title")
        course = Course()
        if request.user.is_authenticated:
            course.author = request.user
        course.title = course_title
        course.technology = request.POST.get("technology")
        course.save()
        chapter1 = create_chapter(course, chapters[0], 0)
        course.current_chapter = chapter1
        theory_blocks = generate_theory(chapters[0], course.technology)
        chapter1.current_theory_number = theory_blocks[0]
        for i in range(len(theory_blocks)):
            new_theory = Theory()
            new_theory.chapter = chapter1
            new_theory.title = theory_blocks[i]["title"]
            new_theory.text = theory_blocks[i]["content"]
            new_theory.order = i
            new_theory.save()

        for i in range(1, len(chapters)):
            create_chapter(course, chapters[i], i)

        return redirect("home")
    context = {}
    return render(request, "create_course.html", context)


def create_chapter(course: Course, name: str, order: int) -> Chapter:
    """
    Создает новую главу в рамках указанного курса.

    Аргументы:
        course (Course): Экземпляр модели Course, к которому будет привязана глава.
        name (str): Название главы.
        order (int): Порядковый номер главы в курсе (используется для сортировки).

    Логика работы:
        1. Инициализирует новый объект модели Chapter.
        2. Устанавливает связь с родительским курсом.
        3. Назначает заголовок и очередность отображения.
        4. Сохраняет запись в базе данных.

    Возвращает:
        Chapter: Созданный и сохраненный объект главы.
    """
    new_chapter = Chapter()
    new_chapter.course = course
    new_chapter.title = name
    new_chapter.order = order
    new_chapter.save()
    return new_chapter


@login_required
def course_page(request, course_id, chapter_id, task_id):
    """
    Отображает страницу урока: теорию, задачу, тесты и историю попыток.

    Управляет прогрессом курса, очищает дубликаты теории и подготавливает
    контекст для рендеринга интерфейса обучения.

    Args:
        request (HttpRequest): HTTP-запрос (требуется авторизация).
        course_id (int): Идентификатор курса.
        chapter_id (int): Порядковый номер главы.
        task_id (int): Порядковый номер теории/задачи.

    Returns:
        HttpResponse: Отрендеренная страница 'course_page.html'.
    """
    course = get_object_or_404(Course, id=course_id)
    course.current_chapter_number = chapter_id
    course.save()
    chapters = Chapter.objects.filter(course=course).order_by("order")
    chapter = Chapter.objects.get(course=course, order=chapter_id)
    chapter.current_task_number = task_id
    chapter.save()
    clean_duplicate_theories(chapter, task_id)
    theory = None
    theory_blocks = Theory.objects.filter(chapter=chapter)
    if theory_blocks:
        theory = Theory.objects.get(chapter=chapter, order=task_id)
    task = None
    tests = None
    if theory:
        try:
            task = Task.objects.get(user=request.user, theory=theory)
            tests = Test.objects.filter(task=task)
        except ObjectDoesNotExist:
            task = Task.objects.create(theory=theory, user=request.user)
    attempts = []
    last_attempt = None
    if task:
        try:
            attempts = Attempt.objects.filter(task=task)
            last_attempt = attempts.first()
            attempts = json.dumps(list(attempts[:5].values()), default=str)
        except ObjectDoesNotExist:
            attempts = []
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
    return render(request, "course_page.html", context)


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
        3. Сбрасывает указатель текущей задачи главы ('current_theory_number') на 0.
        4. В цикле создает и сохраняет новые объекты 'Theory', устанавливая им
           порядковый номер ('order') согласно индексу в списке.
        5. Обновляет состояние главы в базе данных.
        6. Перенаправляет пользователя на страницу первой созданной задачи курса.

    Возвращает:
        HttpResponseRedirect: Редирект на 'course_page' для просмотра созданного контента.
    """
    chapter_id = int(request.POST.get("chapter"))
    course_id = int(request.POST.get("course"))
    chapter = Chapter.objects.get(id=chapter_id)
    course = Course.objects.get(id=course_id)
    theory_blocks = generate_theory(chapter.title, course.technology)
    chapter.current_theory_number = 0
    for i in range(len(theory_blocks)):
        new_theory = Theory()
        new_theory.chapter = chapter
        new_theory.title = theory_blocks[i]["title"]
        new_theory.text = theory_blocks[i]["content"]
        new_theory.order = i
        new_theory.save()
    chapter.save(update_fields=["current_theory_number"])
    return redirect(
        "course_page",
        course_id=course_id,
        chapter_id=chapter.order,
        task_id=chapter.current_theory_number,
    )
