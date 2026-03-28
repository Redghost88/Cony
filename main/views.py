"""
Отвечает за отображения страниц
"""

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout

from cony.forms import LoginForm, RegisterForm
from main.ai_agent import chat
from main.forms import ProfileUpdateForm
from main.models import Chapter, Course, Profile, Task
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required



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
    context = {
        "courses": Course.objects.all()
    }
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
        chapters = request.POST.getlist('chapter_name')

        course = Course()
        if request.user.is_authenticated:
            course.author = request.user
        course.title = "Курс"
        course.technology = request.POST.get("technology")
        course.save()
        chapter1 = create_chapter(course, chapters[0])
        tasks = generate_tasks(chapters[0], course.technology)
        for task in tasks:
            new_task = Task()
            new_task.chapter = chapter1
            new_task.title = task["title"]
            new_task.text = task["content"]
            new_task.save()
        


        for c in chapters[1:]:
            create_chapter(course, c)

        return redirect('home')
    context = {}
    return render(request, "create_course.html", context)

def create_chapter(course: Course, name: str) -> Chapter:
    new_chapter = Chapter()
    new_chapter.course = course
    new_chapter.title = name
    new_chapter.save()
    return new_chapter

def generate_tasks(chapter_name: str, technology: str) -> list:
    """
    - запросить у агента сделать текст с теорией и разбить ее на несколько подглав
    - вернуть теюрию ввиде списка
    """

    prompt = """
    Ты — профессиональный преподаватель и эксперт по созданию учебных материалов по программированию.

    Пользователь передаёт тебе название главы курса и технологию, которая будет извучаться в курсе. Твоя задача — создать качественное теоретическое содержание для этой главы.

    **Инструкции:**

    1. Прочитай название главы курса.
    2. Сгенерируй **5–8 отдельных логически завершённых блоков** теории по данной главе.
    3. Каждый блок должен:
    - Иметь чёткую тему и заголовок
    - Быть самодостаточным (можно читать независимо от других блоков)
    - Содержать объяснение ключевых понятий, принципов или аспектов темы
    - Быть написан понятным, но профессиональным языком
    - Иметь объём примерно 150–350 слов
    - По теме блока можно будет дать задачу в которой пользователь применит новые знания

    4. Структура ответа должна быть строго в следующем формате:

    [
    {
        "title": "Заголовок первого блока",
        "content": "Полный текст теоретического блока..."
    },
    {
        "title": "Заголовок второго блока",
        "content": "Полный текст теоретического блока..."
    },
    ...
    ]

    Важные правила:

    1)Отвечай только массивом из словарей, без каких-либо дополнительных пояснений, приветствий или заключений.
    2)Используй markdown внутри полей "content".
    3)Все блоки должны быть на русском языке.
    4)Содержание должно быть точным, структурированным и педагогически продуманным.
    5)Избегай чрезмерно сложного жаргона, если это не обязательно для темы.
    """

    question = prompt + "\n Название главы:" + chapter_name + ", Название технологии:" + technology
    answer = chat(question)
    return json.loads(answer)

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
    question = request.GET.get("question", "")
    context = {"answer": chat(question)}
    return JsonResponse(context)

def profile(request, username):
    user = get_object_or_404(User, username=username)
    profile_instance, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)
        if form.is_valid():
            form.save()
            return redirect('profile', username=username)
    else:
        form = ProfileUpdateForm(instance=profile_instance)

    context = {
        "profile_user": user,
        "form": form,
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
                return redirect('home')
        context["error"] = "неверный логин или пароль"
    context["form"] = LoginForm()
    return render(request, "login.html", context)

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
    return render(request, 'registration.html', context)

def course_page(request, id):
    course = get_object_or_404(Course, id=id)
    chapters = Chapter.objects.filter(course=course)
    chapter_with_tasks = []
    for chapter in chapters:
        chapter_with_tasks.append({
            "chapter": chapter,
            "tasks": Task.objects.filter(chapter=chapter)
        })

    context = {
        "course": course,
        "chapters": chapters,
        "chapter_with_tasks": chapter_with_tasks
    }
    return render(request, "course_page.html", context)
