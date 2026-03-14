import uuid
import requests
from django.http import JsonResponse
from django.shortcuts import render


from main.ai_agent import chat
from main.models import Chapter, Course


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
    return render(request, 'index.html')

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
        
        return render(request, 'index.html')
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