"""
Отвечает за аутентификацию, регистрацию и управление профилем пользователя.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from main.forms import ProfileUpdateForm, LoginForm, RegisterForm
from main.models import Task, Profile, UserStats
from main.utils import is_yesterday

def profile(request, username):
    """
    Отображает страницу профиля пользователя и обрабатывает обновление данных.

    Args:
        request (HttpRequest): HTTP-запрос.
        username (str): Имя пользователя, чей профиль просматривается.

    Returns:
        HttpResponse: Отрендеренная страница 'profile.html' с формой и статистикой.
    """
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
            return redirect("profile", username=username)
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
    return render(request, "profile.html", context)


def user_login(request):
    """
    Обрабатывает аутентификацию пользователя и вход в систему.

    Args:
        request (HttpRequest): HTTP-запрос с данными формы входа.

    Returns:
        HttpResponse: Редирект на главную страницу или страница логина с ошибкой.
    """
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
                return redirect("home")
        context["error"] = "неверный логин или пароль"
    context["form"] = LoginForm()
    return render(request, "login.html", context)


def check_user_seria(user):
    """Проверяет не закончилась ли серия пользователя"""
    user_stats = UserStats.objects.get(user=user)
    task_complete_date = user_stats.last_task_complete_date
    if task_complete_date is None or not is_yesterday(task_complete_date):
        user_stats.complete_seria = 0
        user_stats.save(update_fields=["complete_seria"])


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
    logout(request)
    return redirect("login")


def registration(request):
    """
    Обрабатывает регистрацию нового пользователя с последующим автоматическим входом.

    Args:
        request (HttpRequest): HTTP-запрос с данными формы регистрации.

    Returns:
        HttpResponse: Страница регистрации или редирект на главную.
    """
    context = {}
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            user_login(request)
            return redirect("home")
    context["form"] = RegisterForm()
    return render(request, "registration.html", context)
