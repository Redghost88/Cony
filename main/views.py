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
    context = {"answer": chat(question)}
    return JsonResponse(context)