"""
Отвечает за отображения страниц
"""

import json
import subprocess
from asyncio import current_task
from email.policy import default

from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods

from cony.forms import LoginForm, RegisterForm
from main.ai_agent import chat
from main.code_checker import check_attempt
from main.forms import ProfileUpdateForm
from main.models import Chapter, Course, Profile, Task, Test, Theory, Attempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

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
    courses = []
    for course in Course.objects.all():
        courses.append(
            [
                course,
                course.current_chapter_number,
                Chapter.objects.get(course=course, order=course.current_chapter_number).current_theory_number,
            ]
        )

    context = {"courses": courses}
    return render(request, "index.html", context)


@login_required
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
        chapters = request.POST.getlist("chapter_name")

        course = Course()
        if request.user.is_authenticated:
            course.author = request.user
        course.title = "Курс"
        course.technology = request.POST.get("technology")
        course.save()
        chapter1 = create_chapter(course, chapters[0], 0)
        course.current_chapter = chapter1
        theory_blocks = generate_theory(chapters[0], course.technology)
        chapter1.current_theory_number = theory_blocks[0]
        for i in range(len(theory_blocks)):
            new_theory = Theory()
            new_theory.chapter = chapter1
            new_theory.title = theory_blocks[i]["title"]
            new_theory.text = theory_blocks[i]["content"]
            new_theory.order = i
            new_theory.save()

        for i in range(1, len(chapters)):
            create_chapter(course, chapters[i], i)

        return redirect("home")
    context = {}
    return render(request, "create_course.html", context)


def create_chapter(course: Course, name: str, order: int) -> Chapter:
    """
    Создаёт новую главу для указанного курса и сохраняет её в базе данных.

    Инициализирует экземпляр модели ``Chapter``, устанавливает связь с курсом,
    задаёт заголовок и порядковый номер, после чего выполняет запись в БД.

    :param course: Экземпляр курса, к которому привязывается новая глава.
    :type course: Course
    :param name: Заголовок (название) главы.
    :type name: str
    :param order: Порядковый номер главы для навигации внутри курса.
    :type order: int

    :return: Сохранённый экземпляр главы с заполненным ``pk``.
    :rtype: Chapter

    :raises django.db.IntegrityError: При нарушении ограничений базы данных
                                      (например, уникальности поля ``order`` в рамках курса).

    .. note::
       Метод ``.save()`` не вызывает валидацию модели (``full_clean()``).
       Если требуется строгая проверка полей перед сохранением, вызовите
       ``new_chapter.full_clean()`` перед ``.save()``.
    """
    new_chapter = Chapter()
    new_chapter.course = course
    new_chapter.title = name
    new_chapter.order = order
    new_chapter.save()
    return new_chapter


def generate_theory(chapter_name: str, technology: str) -> list:
    """
    Генерирует теоретические учебные блоки для указанной главы курса по заданной технологии с использованием ИИ-модели.

    Формирует детальный системный промпт с требованиями к структуре, стилю и объёму материала (5–8 самодостаточных
    блоков на русском языке, с HTML/Bootstrap-разметкой). Отправляет запрос через внешнюю функцию ``chat()``,
    получает ответ в формате JSON-массива и возвращает его в виде списка словарей.

    :param chapter_name: Название главы курса, для которой генерируется теория.
    :type chapter_name: str
    :param technology: Название технологии или языка программирования, изучаемого в курсе.
    :type technology: str
    :return: Список словарей, где каждый элемент содержит ключи ``"title"`` (заголовок блока)
             и ``"content"`` (HTML-размеченный текст теории объёмом 150–350 слов).
    :rtype: list[dict[str, str]]
    :raises json.JSONDecodeError: Если ответ от ИИ-модели не является валидной JSON-строкой.
    """

    prompt = """
    Ты — профессиональный преподаватель и эксперт по созданию учебных материалов по программированию.

    Пользователь передаёт тебе название главы курса и технологию, которая будет извучаться в курсе. Твоя задача — создать качественное теоретическое содержание для этой главы.

    **Инструкции:**

    1. Прочитай название главы курса.
    2. Сгенерируй **5–8 отдельных логически завершённых блоков** теории по данной главе.
    3. Каждый блок должен:
    - Иметь чёткую тему и заголовок
    - Быть самодостаточным (можно читать независимо от других блоков)
    - Содержать объяснение ключевых понятий, принципов или аспектов темы
    - Быть написан понятным, но профессиональным языком
    - Иметь объём примерно 150–350 слов
    - По теме блока можно будет дать задачу в которой пользователь применит новые знания

    4. Структура ответа должна быть строго в следующем формате:

    [
    {
        "title": "Заголовок первого блока",
        "content": "Полный текст теоретического блока..."
    },
    {
        "title": "Заголовок второго блока",
        "content": "Полный текст теоретического блока..."
    },
    ...
    ]

    Важные правила:

    1)Отвечай только массивом из словарей, без каких-либо дополнительных пояснений, приветствий или заключений.
    2)Используй html тэги и bootstrap стили внутри полей "content".
    3)Все блоки должны быть на русском языке.
    4)Содержание должно быть точным, структурированным и педагогически продуманным.
    5)Избегай чрезмерно сложного жаргона, если это не обязательно для темы.
    6)Не создавай задачи внутри полей "content".
    """

    question = prompt + "\n Название главы:" + chapter_name + ", Название технологии:" + technology
    answer = chat(question)
    return json.loads(answer)


@require_http_methods(["POST"])
def generate_tasks(request) -> JsonResponse:
    """
    Генерирует практическое задание и набор тестов с помощью внешней языковой модели
    на основе выбранного теоретического блока и технологии программирования.

    Принимает JSON-запрос, формирует структурированный промпт, отправляет его через
    функцию ``chat()``, парсит ответ ИИ, обновляет данные задачи в базе данных,
    создаёт связанные тесты и возвращает результат в формате JSON.

    :param request: Объект HTTP-запроса. Тело запроса (``request.body``) должно содержать
                    JSON-объект со следующими полями:
                    - ``"technology"`` (``str``): название языка или технологии.
                    - ``"theory"`` (``int`` | ``str``): идентификатор теоретического блока.
                    - ``"task"`` (``int`` | ``str``): идентификатор задания для обновления.
    :type request: django.http.HttpRequest

    :return: JSON-ответ с обновлённым заголовком, содержанием, форматами ввода/вывода
             и массивом сгенерированных тестов.
    :rtype: django.http.JsonResponse

    :raises json.JSONDecodeError: Если тело запроса или ответ от ``chat()`` не являются валидным JSON.
    :raises Theory.DoesNotExist: Если теория с указанным идентификатором не найдена.
    :raises Task.DoesNotExist: Если задание с указанным идентификатором не найдено.
    :raises KeyError: Если структура ответа ИИ не содержит ожидаемых ключей (``title``, ``content`` и др.).
    :raises IndexError: Если ответ ИИ содержит меньше двух элементов (задача и список тестов).

    .. note::
       Функция имеет прямые побочные эффекты: при ``task.is_generated == True`` удаляет
       все существующие тесты, обновляет экземпляр ``Task`` и создаёт новые экземпляры ``Test``.
       Убедитесь, что внешняя функция ``chat()`` настроена на корректную обработку таймаутов
       и возвращает строго валидный JSON без дополнительных текстовых пояснений,
       как указано в системном промпте.
    """
    request_body = json.loads(request.body)
    technology = request_body.get("technology")
    theory = Theory.objects.get(id=int(request_body.get("theory")))
    task = Task.objects.get(id=int(request_body.get("task")))

    if task.is_generated:
        Test.objects.filter(task=task).delete()

    prompt = f"""
    Ты — профессиональный методист онлайн-курсов по программированию. 
    Твоя задача — создавать одну качественную практическую задачу, которая идеально закрепляет материал, пройденный в блоке теории.
    
    Создай **одну** задачу на основе следующего блока теории:
    
    **Язык программирования:** {technology}
    
    **Название блока теории:** {theory.title}
    
    **Содержание блока теории:** 
    {strip_tags(theory.text)}
    
    Дополнительные требования:
    - Задача должна полностью отрабатывать материал из этого блока теории.
    - Не должна требовать знаний, которые ещё не были пройдены.
    - Должна быть интересной и с небольшим реальным контекстом.
    - Уровень сложности должен соответствовать уровню блока (не слишком простой и не слишком сложный).
    - Обязательно напиши 4 примера входа/выхода."""

    structure = """
    Структура ответа должна быть строго в следующем формате:

    [
    {
        "title": "Название задачи",
        "content": "подробное и понятное описание задачи на русском языке",
        "input_data": "формат ввода",
        "output_data": "что должна вернуть программа"
    },
    [
        ["пример входных данных первого теста", "пример выходных данных первого теста"],
        ["пример входных данных второго теста", "пример выходных данных второго теста"],
        ...
    ],
    ]
    
    Важные правила:

    1)Отвечай только массивом из словарей, без каких-либо дополнительных пояснений, приветствий или заключений.
    2)Используй html тэги и bootstrap стили внутри полей "content".
    3)Все блоки должны быть на русском языке.
    4)Содержание должно быть точным, структурированным и педагогически продуманным.
    5)Избегай чрезмерно сложного жаргона, если это не обязательно для темы.
    6)В поле "content" не пиши формат для входных и выходных данных
    7)Не пиши решение задачи. Только задачу.
    8)В полях input_data и output_data пиши только описание формата входных и выходных данных и их ограничений
    """
    question = prompt + structure
    answer = json.loads(chat(question))
    task_info = answer[0]
    tests_info = answer[1]
    task.title = task_info["title"]
    task.task_content = task_info["content"]
    task.input_data = task_info["input_data"]
    task.output_data = task_info["output_data"]
    task.is_generated = True
    task.save()
    response = {
        "task_title": task.title,
        "task_text": task.task_content,
        "input_data": task.input_data,
        "output_data": task.output_data,
        "tests": [],
    }
    tests = []
    for i in range(len(tests_info)):
        test = Test.objects.create(task=task, input_data=tests_info[i][0], output_data=tests_info[i][1], order=i)
        tests.append({"input_data": test.input_data, "output_data": test.output_data})
    response["tests"] = tests

    return JsonResponse(response)


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
    question = request.GET.get("question", "")
    context = {"answer": chat(question)}
    return JsonResponse(context)


def profile(request, username):
    """
    Отображает страницу профиля пользователя и обрабатывает обновление данных текущего пользователя.

    - **GET**: Инициализирует форму ``ProfileUpdateForm`` с текущими данными профиля и отображает
      шаблон ``profile.html``.
    - **POST**: Валидирует данные формы. При успешной валидации сохраняет изменения и перенаправляет
      на ту же страницу профиля. В случае ошибок форма возвращается с сообщениями валидации.

    В контекст шаблона передаются:
    - ``profile_user``: объект пользователя, чей профиль просматривается (по ``username``).
    - ``form``: экземпляр формы обновления профиля, привязанный к профилю текущего пользователя
      (``request.user``).

    :param request: HTTP-запрос.
    :type request: django.http.HttpRequest
    :param username: Имя пользователя, чей профиль отображается.
    :type username: str
    :return: Отрендеренный HTML-шаблон страницы профиля.
    :rtype: django.http.HttpResponse
    :raises Http404: Если пользователь с указанным ``username`` не найден.
    """
    user = get_object_or_404(User, username=username)
    profile_instance, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)
        if form.is_valid():
            form.save()
            return redirect("profile", username=username)
    else:
        form = ProfileUpdateForm(instance=profile_instance)

    context = {
        "profile_user": user,
        "form": form,
    }
    return render(request, "profile.html", context)


def user_login(request):
    """
    Обрабатывает вход пользователя в систему.

    При **GET-запросе** возвращает страницу с формой авторизации.
    При **POST-запросе** валидирует данные формы, выполняет аутентификацию
    и в случае успеха авторизует пользователя с перенаправлением на страницу ``home``.
    При неудачной попытке форма возвращается с сообщением об ошибке.

    :param request: Объект HTTP-запроса.
    :type request: django.http.HttpRequest

    :return: Отрендеренный шаблон ``login.html`` или перенаправление на ``home``.
    :rtype: django.http.HttpResponse | django.http.HttpResponseRedirect

    **Контекст шаблона** (передаётся в ``login.html``):
      - ``form``: экземпляр ``LoginForm`` для рендеринга полей ввода.
      - ``error``: строка с текстом ошибки (добавляется в контекст только при неверных учётных данных).

    .. note::
       Предназначена исключительно для неавторизованных пользователей. Убедитесь, что URL-маршрут ``login``
       не обернут в ``@login_required`` и доступен без аутентификации в конфигурации проекта.
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
                return redirect("home")
        context["error"] = "неверный логин или пароль"
    context["form"] = LoginForm()
    return render(request, "login.html", context)


def user_logout(request):
    """
    Выполняет выход текущего пользователя из системы и перенаправляет на страницу авторизации.

    Завершает активную сессию, очищает данные аутентификации из объекта запроса
    и возвращает HTTP-ответ с перенаправлением на URL, привязанный к имени ``login``.

    :param request: Объект HTTP-запроса.
    :type request: django.http.HttpRequest

    :return: Ответ с перенаправлением (HTTP 302) на страницу входа.
    :rtype: django.http.HttpResponseRedirect

    .. note::
       Функция безопасна для вызова без авторизации: встроенный ``django.contrib.auth.logout()``
       корректно обрабатывает отсутствие активной сессии и не генерирует исключений.
    """
    logout(request)
    return redirect("login")


def registration(request):
    """
    Обрабатывает GET и POST-запросы для регистрации нового пользователя.

    - **GET**: Инициализирует пустую форму ``RegisterForm`` и отображает шаблон
      ``registration.html``.
    - **POST**: Валидирует данные формы. При успешной валидации сохраняет пользователя,
      вызывает ``user_login(request)`` для автоматической авторизации и перенаправляет
      на URL с именем ``"home"``. При ошибках валидации шаблон возвращается с
      заполненной формой и сообщениями об ошибках.

    :param request: HTTP-запрос, содержащий данные формы (при POST).
    :type request: django.http.HttpRequest
    :return: Отрендеренный HTML-шаблон или объект перенаправления.
    :rtype: django.http.HttpResponse
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


@login_required
def course_page(request, course_id, chapter_id, task_id):
    """
    Отображает страницу прохождения курса с выбранной главой и заданием.

    Загружает информацию о курсе, обновляет текущую главу и задачу,
    получает теоретические блоки, связанные тесты и историю попыток пользователя.
    Если задание для текущего пользователя ещё не создано, оно создаётся автоматически.

    :param request: Объект HTTP-запроса.
    :type request: django.http.HttpRequest
    :param course_id: Уникальный идентификатор курса в базе данных.
    :type course_id: int
    :param chapter_id: Порядковый номер главы внутри курса (используется для фильтрации и навигации).
    :type chapter_id: int
    :param task_id: Порядковый номер теоретического блока/задания внутри главы.
    :type task_id: int

    :return: Отрендеренный ответ с шаблоном ``course_page.html``.
    :rtype: django.http.HttpResponse

    :raises django.http.Http404: Если курс с указанным ``course_id`` не найден.
    :raises <Model>.DoesNotExist: Если глава или теоретический блок не найдены по переданным порядковым номерам.
    :raises django.core.exceptions.PermissionDenied: Если пользователь не авторизован (контролируется ``@login_required``).

    .. note::
       Функция имеет побочные эффекты: при каждом вызове в базу данных записываются
       обновлённые значения полей ``current_chapter_number`` (модель ``Course``) и
       ``current_task_number`` (модель ``Chapter``).
    """
    course = get_object_or_404(Course, id=course_id)
    course.current_chapter_number = chapter_id
    course.save()
    chapters = Chapter.objects.filter(course=course)
    chapter = Chapter.objects.get(course=course, order=chapter_id)
    chapter.current_task_number = task_id
    chapter.save()
    theory_blocks = Theory.objects.filter(chapter=chapter)
    theory = None
    if theory_blocks:
        theory = Theory.objects.get(chapter=chapter, order=task_id)
    task = None
    tests = None
    if theory:
        try:
            task = Task.objects.get(user=request.user, theory=theory)
            tests = Test.objects.filter(task=task)
        except ObjectDoesNotExist:
            task = Task.objects.create(theory=theory, user=request.user)
    attempts = []
    if task:
        try:
            attempts = Attempt.objects.filter(task=task)
        except ObjectDoesNotExist:
            attempts = []

    context = {
        "course": course,
        "chapters": chapters,
        "chapter": chapter,
        "theory_blocks": theory_blocks,
        "theory": theory,
        "task": task,
        "tests": tests,
        "attempts": json.dumps(list(attempts[:5].values()), default=str),
    }
    return render(request, "course_page.html", context)


@require_http_methods(["POST"])
def run_code(request):
    """
    Выполняет пользовательский Python-код и возвращает результат его выполнения.

    Ожидает, что тело запроса содержит JSON-строку с исходным кодом (например,
    ``"print('Hello')"``). Код запускается через системный интерпретатор Python
    с ограничением времени выполнения (``5`` секунд). Возвращает ``stdout``;
    если он пуст, возвращается ``stderr``. При превышении времени или возникновении
    других исключений возвращает JSON-ответ с описанием проблемы в поле ``error``.

    :param request: HTTP-запрос, содержащий JSON-строку с исходным кодом.
    :type request: django.http.HttpRequest
    :return: JSON-ответ с полем ``output`` (успешный вывод) или ``error`` (ошибка/таймаут).
    :rtype: django.http.JsonResponse
    :raises json.JSONDecodeError: Если тело запроса не является валидным JSON.
    """
    code = json.loads(request.body)
    code_timeout = 5
    try:
        process = subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=code_timeout)
        output = process.stdout if process.stdout else process.stderr
        return JsonResponse({"output": output})
    except subprocess.TimeoutExpired:
        return JsonResponse({"error": f"Превышено время выполнения программы ({code_timeout} секунд)"})
    except Exception as e:
        return JsonResponse({"error": str(e)})


@require_http_methods(["POST"])
def check_code(request):
    """
    Обрабатывает POST-запросы для проверки исходного кода конкретной задачи.

    Ожидает JSON-тело запроса с полями ``source_code`` (str) и ``task_id`` (int).
    Создаёт новую попытку, проверяет её через ``check_attempt()``, и при успешном
    прохождении обновляет статус ``decided`` у задачи. Возвращает объект с полём
    ``attempts``, содержащим JSON-сериализованную строку списка последних 5 попыток.

    :param request: HTTP-запрос, содержащий JSON-полезную нагрузку.
    :type request: django.http.HttpRequest
    :return: JSON-ответ с сериализованными данными попыток.
    :rtype: django.http.JsonResponse
    :raises Task.DoesNotExist: Если задача с указанным ``task_id`` не найдена.
    :raises KeyError: Если в теле запроса отсутствуют поля ``source_code`` или ``task_id``.
    :raises json.JSONDecodeError: Если тело запроса не является валидным JSON.
    """
    code = json.loads(request.body)["source_code"]
    task_id = int(json.loads(request.body)["task_id"])
    task = Task.objects.get(id=task_id)
    attempt = Attempt.objects.create(task=task, user=request.user, source_code=code)
    check_attempt(attempt)
    if attempt.passed:
        task.decided = True
        task.save(update_fields=["decided"])
    attempts = Attempt.objects.filter(task=task)
    return JsonResponse({"attempts": json.dumps(list(attempts[:5].values()), default=str)})
