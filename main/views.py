"""
Отвечает за отображения страниц
"""
from django.http import JsonResponse
from django.shortcuts import render


from main.ai_agent import chat


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
    question_settings = ["Пиши как учитель",
    "Напиши только пункты для изучения и их краткое описание неболее 30 слов",
    "Перед номером каждого пункта пиши '#####' а после сам номер"]
    chat_request = question + ". " + ". ".join(question_settings)
    context = {"answer": chat(chat_request)}
    return JsonResponse(context)