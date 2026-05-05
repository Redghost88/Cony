"""
Отвечает за отображения страниц
"""

import json
import subprocess
from asyncio import current_task
from email.policy import default

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods

from datetime import datetime, timedelta
from main.ai_agent import chat
from main.code_checker import check_attempt
from main.forms import ProfileUpdateForm, LoginForm, RegisterForm
from main.models import Chapter, Course, Profile, Task, Test, Theory, Attempt, UserStats
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from main.prompts import STYLE_RULES, GENERATE_THEORY, GENERATE_TASK

# Create your views here.


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
                Chapter.objects.get(course=course, order=course.current_chapter_number).current_theory_number,
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
    new_chapter = Chapter()
    new_chapter.course = course
    new_chapter.title = name
    new_chapter.order = order
    new_chapter.save()
    return new_chapter


def generate_theory(chapter_name: str, technology: str) -> list:
    question = GENERATE_THEORY + STYLE_RULES + "\n Название главы:" + chapter_name + ", Название технологии:" + technology
    answer = chat(question)
    return json.loads(answer)


@require_http_methods(["POST"])
def generate_tasks(request) -> JsonResponse:
    request_body = json.loads(request.body)
    technology = request_body.get("technology")
    theory = Theory.objects.get(id=int(request_body.get("theory")))
    task = Task.objects.get(id=int(request_body.get("task")))

    if task.is_generated:
        Test.objects.filter(task=task).delete()

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
        test = Test.objects.create(task=task, input_data=tests_info[i][0], output_data=tests_info[i][1], order=i)
        tests.append({"input_data": test.input_data, "output_data": test.output_data})
    response["tests"] = tests

    return JsonResponse(response)


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
    question = STYLE_RULES + request.GET.get("question", "")
    context = {"answer": chat(question)}
    return JsonResponse(context)


def profile(request, username):
    user = get_object_or_404(User, username=username)
    profile_instance, created = Profile.objects.get_or_create(user=request.user)
    count_of_decided_tasks = Task.objects.filter(user=request.user, decided=True).count()
    count_of_undecided_tasks = Task.objects.filter(user=request.user, decided=False).count()

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)
        if form.is_valid():
            form.save()
            return redirect("profile", username=username)
    else:
        form = ProfileUpdateForm(instance=profile_instance)

    user_stats = UserStats.objects.get(user=request.user)

    context = {
        "profile_user": user,
        "form": form,
        "count_of_decided_tasks": count_of_decided_tasks,
        "count_of_undecided_tasks": count_of_undecided_tasks,
        "complete_streak": user_stats.complete_seria,
        "max_seria": user_stats.max_seria,
    }
    return render(request, "profile.html", context)


def user_login(request):
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
                    user_stats = UserStats.objects.get(user=request.user)
                    task_complete_date = user_stats.last_task_complete_date
                    if task_complete_date is None or not is_yesterday(task_complete_date):
                        user_stats.complete_seria = 0
                        user_stats.save(update_fields=["complete_seria"])
                else:
                    UserStats.objects.create(user=request.user)
                return redirect("home")
        context["error"] = "неверный логин или пароль"
    context["form"] = LoginForm()
    return render(request, "login.html", context)

def is_yesterday(date):
    """Проверяет, была ли дата вчера"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    return date.date() == yesterday

def user_logout(request):
    logout(request)
    return redirect("login")


def registration(request):
    context = {}
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            user_login(request)
            return redirect("home")
    context["form"] = RegisterForm()
    return render(request, "registration.html", context)


@login_required
def course_page(request, course_id, chapter_id, task_id):
    course = get_object_or_404(Course, id=course_id)
    course.current_chapter_number = chapter_id
    course.save()
    chapters = Chapter.objects.filter(course=course)
    chapter = Chapter.objects.get(course=course, order=chapter_id)
    chapter.current_task_number = task_id
    chapter.save()
    theory_blocks = Theory.objects.filter(chapter=chapter)
    for i in range(len(theory_blocks)):
        theory_same_order = Theory.objects.filter(chapter=chapter, order=task_id)
        if len(theory_same_order) > 1:
            for t in theory_same_order[1:]:
                t.delete()
    theory = None
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
    code = ""
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
def run_code(request):
    request_body = json.loads(request.body)
    code = request_body.get("code")
    input_data = request_body.get("input_data")
    code_timeout = 5
    try:
        process = subprocess.run(
            ["python", "-c", code], input=input_data, capture_output=True, text=True, timeout=code_timeout
        )
        if process.stdout:
            output = process.stdout
        else:
            output = '<div style="color: #dc3545;">' + process.stderr + "</div>"
        return JsonResponse({"output": output})
    except subprocess.TimeoutExpired:
        return JsonResponse({"error": f"Превышено время выполнения программы ({code_timeout} секунд)"})
    except Exception as e:
        return JsonResponse({"error": str(e)})


@require_http_methods(["POST"])
def check_code(request):
    code = json.loads(request.body)["source_code"]
    task_id = int(json.loads(request.body)["task_id"])
    task = Task.objects.get(id=task_id)
    attempt = Attempt.objects.create(task=task, user=request.user, source_code=code)
    check_attempt(attempt)
    if attempt.passed:
        task.decided = True
        task.save(update_fields=["decided"])
        course_id = json.loads(request.body)["course_id"]
        course = Course.objects.get(id=course_id)
        update_course_progress(course, request.user)
        user_stat = UserStats.objects.get(user=request.user)
        task_complete_date = user_stat.last_task_complete_date
        if task_complete_date is None or is_yesterday(task_complete_date):
            user_stat.complete_seria += 1
        user_stat.last_task_complete_date = datetime.now().date()
        user_stat.save(update_fields=["last_task_complete_date", "complete_seria"])
    attempts = Attempt.objects.filter(task=task)
    return JsonResponse({"attempts": json.dumps(list(attempts[:5].values()), default=str)})


def update_course_progress(course, user) -> None:
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


@require_http_methods(["POST"])
def add_new_theory(request):
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
    return redirect("course_page", course_id=course_id, chapter_id=chapter.order, task_id=chapter.current_theory_number)
