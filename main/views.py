"""
Отвечает за отображения страниц
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout

from cony.forms import LoginForm, RegisterForm
from main.ai_agent import chat
from main.forms import ProfileUpdateForm
from main.models import Chapter, Course, Profile, Task
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User



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
        course.save()

        for chapter in chapters:
            new_chapter = Chapter()
            new_chapter.course = course
            new_chapter.title = chapter
            new_chapter.save()

        return redirect('home')
    context = {}
    return render(request, "create_course.html", context)

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
