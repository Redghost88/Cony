import uuid
import requests
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout

from cony.forms import LoginForm, RegisterForm
from main.ai_agent import chat


# Create your views here.

def home(request):
    return render(request, 'index.html')

def create_course(request):
    context = {}
    return render(request, 'create_course.html', context)

def generate_answer(request):
    question = request.GET.get('question', '')
    question_settings = ["Пиши как учитель", "Напиши только пункты для изучения и их краткое описание неболее 30 слов",
    "Перед номером каждого пункта пиши '#####' а после сам номер"]
    chat_request = question + ". " + ". ".join(question_settings)
    context = {"answer": chat(chat_request)}
    return JsonResponse(context)

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
