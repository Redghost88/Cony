import uuid
import requests
from django.shortcuts import render
from gigachat import GigaChat

from cony.settings import GIGACHAT_AUTH_TOKEN


# Create your views here.

def home(request):
    return render(request, 'index.html')

def create_course(request):
    context = {}
    giga = GigaChat(
        credentials=GIGACHAT_AUTH_TOKEN
    )

    response = giga.chat("Напиши 10 тем для изучения в питоне кратко")

    context["answer"] = response.choices[0].message.content
    return render(request, 'create_course.html', context)
