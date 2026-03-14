import uuid
import requests
from django.http import JsonResponse
from django.shortcuts import render


from main.ai_agent import chat
from main.models import Chapter, Course


# Create your views here.

def home(request):
    return render(request, 'index.html')

def create_course(request):
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
        
        return render(request, 'index.html')
    context = {}
    return render(request, 'create_course.html', context)

def generate_answer(request):
    question = request.GET.get('question', '')
    context = {"answer": chat(question)}
    return JsonResponse(context)