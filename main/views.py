import uuid
import requests
from django.http import JsonResponse
from django.shortcuts import render

from main.ai_agent import chat
from main.models import Chapter, Course
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User

from main.forms import ProfileUpdateForm
from main.models import Profile


#from cony.settings import GIGACHAT_AUTH_TOKEN

# Create your views here.

def home(request):
    print("gggggg")
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
    print(context)
    return render(request, 'index.html', context)

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
    return render(request, 'create_course.html', context)

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
    question = request.GET.get('question', '')
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
