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

def practice(request, ):
    context = {}
    if ()
        return render(request, 'registration.html',context)