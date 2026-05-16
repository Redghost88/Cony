"""
Отвечает за отображения страниц
"""

import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from main.ai_agent import chat
from main.forms import ProfileUpdateForm, LoginForm, RegisterForm
from main.models import Chapter, Course, Profile, Task, Test, Theory, Attempt, UserStats
from main.tasks import send_attempt, test_user_code
from main.utils import clean_duplicate_theories, is_yesterday, update_course_progress
from main.prompts import (
    CHAT_SETTINGS,
    GENERATE_COURSE,
    STYLE_RULES,
    GENERATE_THEORY,
    GENERATE_TASK,
)

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

        logger.info(f"Курс создан: ID={course.id}, название='{course.title}', автор={request.user}, глав={len(chapters)}")
        return redirect("home")
    context = {}
    logger.info("Отображена форма создания курса")
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
    logger.debug(f"Создана глава: ID={new_chapter.id}, название='{name}', порядок={order}, курс={course.id}")
    return new_chapter


def generate_theory(chapter_name: str, technology: str) -> list:
    """
    Генерирует структурированный учебный контент с использованием AI.

    Формирует промпт, отправляет запрос к нейросети и парсит ответ в список словарей.

    Args:
        chapter_name (str): Название учебной темы.
        technology (str): Изучаемая технология (например, 'Python').

    Returns:
        list: Список словарей с ключами 'title' и 'content'.

    Raises:
        json.JSONDecodeError: Если ответ от AI не является валидным JSON.
    """
    logger.info(f"Генерация теории: глава='{chapter_name}', технология='{technology}'")
    prompt = GENERATE_THEORY + STYLE_RULES
    question = (
        prompt
        + "\n Название главы:"
        + chapter_name
        + ", Название технологии:"
        + technology
    )
    try:
        answer = chat(question)
        result = json.loads(answer)
        logger.info(f"Теория сгенерирована успешно: блоков={len(result)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON при генерации теории: {e}, ответ AI: {answer[:200]}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации теории: {e}")
        raise


@require_http_methods(["POST"])
def generate_tasks(request) -> JsonResponse:
    """
    Генерирует практическую задачу и тесты на основе теоретического блока через AI.

    Извлекает ID теории и задачи, удаляет старые тесты, формирует промпт,
    парсит ответ AI и сохраняет новую задачу с тестовыми случаями в БД.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'technology': str, 'theory': int, 'task': int}.

    Returns:
        JsonResponse: Данные новой задачи и списка тестов для фронтенда.
    """
    logger.info(f"Генерация задач запрошена пользователем: {request.user}")
    try:
        request_body = json.loads(request.body)
        technology = request_body.get("technology")
        theory = Theory.objects.get(id=int(request_body.get("theory")))
        task = Task.objects.get(id=int(request_body.get("task")))

        logger.info(f"Генерация задачи: технология='{technology}', теория ID={theory.id}, задача ID={task.id}")

        if task.is_generated:
            Test.objects.filter(task=task).delete()
            logger.debug(f"Удалены старые тесты для задачи ID={task.id}")

        question = GENERATE_TASK % (technology, theory.title, strip_tags(theory.text))
        answer = json.loads(chat(question))
        task_info = answer[0]
        tests_info = answer[1]
        task.title = task_info["title"]
        task.task_content = task_info["content"]
        task.input_data = task_info["input_data"]
        task.output_data = task_info["output_data"]
        task.is_generated = True
        task.save()
        response = {
            "task_title": task.title,
            "task_text": task.task_content,
            "input_data": task.input_data,
            "output_data": task.output_data,
            "tests": [],
        }
        tests = []
        for i in range(len(tests_info)):
            test = Test.objects.create(
                task=task,
                input_data=tests_info[i][0],
                output_data=tests_info[i][1],
                order=i,
            )
            tests.append({"input_data": test.input_data, "output_data": test.output_data})
        response["tests"] = tests

        logger.info(f"Задача сгенерирована успешно: ID={task.id}, тестов={len(tests)}")
        return JsonResponse(response)
    except Exception as e:
        logger.error(f"Ошибка при генерации задач: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def generate_course(request):
    """
    Генерирует структуру курса на основе пользовательского запроса.

    Args:
        request (HttpRequest): GET-запрос с параметром 'question'.

    Returns:
        JsonResponse: JSON-ответ с полем 'answer', содержащим сгенерированный контент.
    """
    question_text = request.GET.get("question", "")
    logger.info(f"Генерация курса запрошена: вопрос='{question_text[:100]}...'")
    question = GENERATE_COURSE + question_text
    context = {"answer": chat(question)}
    logger.info("Курс сгенерирован успешно")
    return JsonResponse(context)


def generate_chat_answer(request):
    """
    Отвечает на вопрос пользователя в чате, используя системные инструкции AI.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'question': str}.

    Returns:
        JsonResponse: JSON-ответ с полем 'answer'.
    """
    try:
        request_body = json.loads(request.body)
        question_text = request_body.get("question", "")
        logger.info(f"Чат-ответ запрошен: вопрос='{question_text[:100]}...'")
        question = CHAT_SETTINGS + "\n" + question_text
        print(question)
        context = {"answer": chat(question)}
        logger.info("Чат-ответ сгенерирован успешно")
        return JsonResponse(context)
    except Exception as e:
        logger.error(f"Ошибка при генерации чат-ответа: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def generate_answer(request):
    """
    Обрабатывает GET-запрос с параметром ``question``, добавляет системные инструкции
    к запросу и отправляет его в функцию :func:`~core.utils.chat`. Возвращает ответ
    в формате JSON для использования в AJAX-запросах.

    :param request: Объект HTTP-запроса Django.
    :type request: HttpRequest
    :return: JSON-ответ с полем ``answer``, содержащим сгенерированный текст.
    :rtype: JsonResponse

    :query string question: Текст вопроса от пользователя (обязательный параметр).
    :query string: Если параметр ``question`` отсутствует, используется пустая строка.

    """
    question_text = request.GET.get("question", "")
    logger.info(f"Генерация ответа запрошена: вопрос='{question_text[:100]}...'")
    question = STYLE_RULES + question_text
    context = {"answer": chat(question)}
    logger.info("Ответ сгенерирован успешно")
    return JsonResponse(context)


def profile(request, username):
    """
    Отображает страницу профиля пользователя и обрабатывает обновление данных.

    Args:
        request (HttpRequest): HTTP-запрос.
        username (str): Имя пользователя, чей профиль просматривается.

    Returns:
        HttpResponse: Отрендеренная страница 'profile.html' с формой и статистикой.
    """
    logger.info(f"Профиль запрошен: username='{username}', запрашивающий={request.user}")
    user = get_object_or_404(User, username=username)
    profile_instance, created = Profile.objects.get_or_create(user=request.user)
    count_of_decided_tasks = Task.objects.filter(
        user=request.user, decided=True
    ).count()
    count_of_undecided_tasks = Task.objects.filter(
        user=request.user, decided=False
    ).count()

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)
        if form.is_valid():
            form.save()
            logger.info(f"Профиль обновлен: пользователь={request.user}")
            return redirect("profile", username=username)
        else:
            logger.warning(f"Ошибка валидации формы профиля: пользователь={request.user}, ошибки={form.errors}")
    else:
        form = ProfileUpdateForm(instance=profile_instance)

    check_user_seria(request.user)
    user_stats = UserStats.objects.get(user=request.user)

    context = {
        "profile_user": user,
        "form": form,
        "count_of_decided_tasks": count_of_decided_tasks,
        "count_of_undecided_tasks": count_of_undecided_tasks,
        "complete_streak": user_stats.complete_seria,
        "max_seria": user_stats.max_seria,
    }
    logger.info(f"Профиль отображен: username='{username}', решенных задач={count_of_decided_tasks}, серия={user_stats.complete_seria}")
    return render(request, "profile.html", context)


def user_login(request):
    """
    Обрабатывает аутентификацию пользователя и вход в систему.

    Args:
        request (HttpRequest): HTTP-запрос с данными формы входа.

    Returns:
        HttpResponse: Редирект на главную страницу или страница логина с ошибкой.
    """
    logger.info(f"Попытка входа в систему")
    context = {}
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if UserStats.objects.filter(user=request.user).exists():
                    check_user_seria(request.user)
                else:
                    UserStats.objects.create(user=request.user)
                logger.info(f"Успешный вход: пользователь='{username}'")
                return redirect("home")
            else:
                logger.warning(f"Неудачная попытка входа: пользователь='{username}'")
        context["error"] = "неверный логин или пароль"
        logger.warning(f"Ошибка валидации формы входа")
    context["form"] = LoginForm()
    logger.info("Отображена форма входа")
    return render(request, "login.html", context)


def check_user_seria(user):
    """Проверяет не закончилась ли серия пользователя"""
    user_stats = UserStats.objects.get(user=user)
    task_complete_date = user_stats.last_task_complete_date
    if task_complete_date is None or not is_yesterday(task_complete_date):
        user_stats.complete_seria = 0
        user_stats.save(update_fields=["complete_seria"])
        logger.debug(f"Сброшена серия пользователя: {user.username}")


def user_logout(request):
    """
    Завершает текущую сессию пользователя и выполняет выход из системы.

    Аргументы:
        request (HttpRequest): Объект запроса Django.

    Логика работы:
        1. Вызывает стандартную функцию Django `logout()`, которая удаляет ID пользователя
           из текущей сессии и очищает данные сессии.
        2. После успешного выхода перенаправляет пользователя на страницу входа.

    Возвращает:
        HttpResponseRedirect: Перенаправление на именованный URL-адрес 'login'.
    """
    logger.info(f"Выход из системы: пользователь={request.user}")
    logout(request)
    logger.info(f"Успешный выход из системы")
    return redirect("login")


def registration(request):
    """
    Обрабатывает регистрацию нового пользователя с последующим автоматическим входом.

    Args:
        request (HttpRequest): HTTP-запрос с данными формы регистрации.

    Returns:
        HttpResponse: Страница регистрации или редирект на главную.
    """
    logger.info(f"Регистрация нового пользователя")
    context = {}
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.info(f"Пользователь зарегистрирован: username='{user.username}'")
            user_login(request)
            return redirect("home")
        else:
            logger.warning(f"Ошибка валидации формы регистрации: ошибки={form.errors}")
    context["form"] = RegisterForm()
    logger.info("Отображена форма регистрации")
    return render(request, "registration.html", context)


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
    logger.info(f"Страница курса запрошена: пользователь={request.user}, курс={course_id}, глава={chapter_id}, задача={task_id}")
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
            logger.debug(f"Создана новая задача: ID={task.id}, теория={theory.id}, пользователь={request.user}")
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
    logger.info(f"Страница курса отображена: курс='{course.title}', глав={len(chapters)}, теорий={len(theory_blocks)}")
    return render(request, "course_page.html", context)


@require_http_methods(["POST"])
def run_code(request):
    """
    Выполняет пользовательский Python-код в изолированном Docker-контейнере.

    Принимает код и входные данные, запускает асинхронную задачу Celery
    и ожидает результат выполнения.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'code': str, 'input_data': str}.

    Returns:
        JsonResponse: {'output': str} при успехе или {'error': str} при ошибке.
    """
    logger.info(f"Выполнение кода запрошено пользователем: {request.user}")
    try:
        request_body = json.loads(request.body)
        code = request_body.get("code")
        input_data = request_body.get("input_data")
        code_timeout = 2
        logger.debug(f"Выполнение кода: длина кода={len(code)}, входные данные='{input_data[:100] if input_data else 'нет'}'")
        
        async_result = test_user_code.apply_async(
            args=[code, input_data, code_timeout]
        ).get(timeout=code_timeout)

        if async_result["stdout"]:
            output = async_result["stdout"]
            logger.info(f"Код выполнен успешно: вывод='{output[:100]}...'")
        else:
            output = '<div style="color: #dc3545;">' + async_result["stderr"] + "</div>"
            logger.warning(f"Ошибка выполнения кода: ошибка='{async_result['stderr'][:200]}'")
        return JsonResponse({"output": output})
    except Exception as e:
        logger.error(f"Исключение при выполнении кода: {e}")
        return JsonResponse({"error": str(e)})


@require_http_methods(["POST"])
def check_code(request):
    """
    Создаёт попытку решения задачи и запускает её асинхронную проверку.

    Args:
        request (HttpRequest): POST-запрос с JSON: {'source_code': str, 'task_id': int, 'course_id': int}.

    Returns:
        JsonResponse: Список последних 5 попыток пользователя.
    """
    logger.info(f"Проверка кода запрошена пользователем: {request.user}")
    try:
        data = json.loads(request.body)
        code = data["source_code"]
        task_id = int(data["task_id"])
        task = Task.objects.get(id=task_id)
        attempt = Attempt.objects.create(task=task, user=request.user, source_code=code)
        course_id = data["course_id"]
        send_attempt.delay(attempt.id, course_id)

        attempts = Attempt.objects.filter(task=task)
        logger.info(f"Попытка создана: ID={attempt.id}, задача={task_id}, курс={course_id}, длина кода={len(code)}")
        return JsonResponse({"attempts": list(attempts[:5].values())})
    except Exception as e:
        logger.error(f"Ошибка при создании попытки: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def get_task_attempts(request, task_id):
    """Возвращает все попытки решения пользователем конкретной задачи"""
    logger.info(f"Запрос попыток задачи: задача={task_id}, пользователь={request.user}")
    task = Task.objects.get(id=task_id)
    attempts = Attempt.objects.filter(task=task)
    logger.info(f"Возвращено попыток: {attempts.count()} для задачи={task_id}")
    return JsonResponse({"attempts": list(attempts[:5].values())})


@require_http_methods(["GET"])
def get_attempt_status(request, attempt_id):
    """Возвращает текущий статус проверки."""
    logger.info(f"Запрос статуса попытки: ID={attempt_id}, пользователь={request.user}")
    try:
        attempt = Attempt.objects.only("status", "passed", "check_log").get(
            id=attempt_id
        )
        logger.info(f"Статус попытки: ID={attempt_id}, статус={attempt.status}, пройдено={attempt.passed}")
        return JsonResponse(
            {
                "status": attempt.status,
                "passed": attempt.passed,
                "check_log": attempt.check_log,
            }
        )
    except Attempt.DoesNotExist:
        logger.error(f"Попытка не найдена: ID={attempt_id}")
        return JsonResponse({"error": "Not found"})


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
    logger.info(f"Добавление новой теории запрошено пользователем: {request.user}")
    chapter_id = int(request.POST.get("chapter"))
    course_id = int(request.POST.get("course"))
    chapter = Chapter.objects.get(id=chapter_id)
    course = Course.objects.get(id=course_id)
    logger.info(f"Добавление теории: глава ID={chapter_id} '{chapter.title}', курс ID={course_id} '{course.title}'")
    
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
    
    logger.info(f"Теория добавлена: блоков={len(theory_blocks)}, глава={chapter.title}")
    return redirect(
        "course_page",
        course_id=course_id,
        chapter_id=chapter.order,
        task_id=chapter.current_theory_number,
    )