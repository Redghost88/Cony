import uuid
import requests
from django.http import JsonResponse
from django.shortcuts import render


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

def start_view(request):
    return render(request, 'start.html')
def start_reasons_view(request):
    return render(request, 'start_reasons.html')
def start_descr_view(request):
    return render(request, 'start_descr.html')
def start_exp_view(request):
    return render(request, 'start_exp.html')
def start_aspect_view(request):
    return render(request, 'start_aspect.html')
def start_aspect_frontend_view(request):
    return render(request, 'start_aspect_frontend.html')
def start_aspect_backend_view(request):
    return render(request, 'start_aspect_backend.html')
def start_aspect_fullstack_view(request):
    return render(request, 'start_aspect_fullstack.html')


def logout_view(request):
    logout(request)
    return redirect('/')