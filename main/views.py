"""
Отвечает за отображения страниц
"""

import json
import subprocess
from asyncio import current_task
from email.policy import default

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods

from main.ai_agent import chat
from main.code_checker import check_attempt
from main.forms import ProfileUpdateForm, LoginForm, RegisterForm
from main.models import Chapter, Course, Profile, Task, Test, Theory, Attempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from main.prompts import STYLE_RULES

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
        course_title = request.POST.get("course_title")
        course = Course()
        if request.user.is_authenticated:
            course.author = request.user
        course.title = course_title
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
        Создает новую главу в рамках указанного курса.

        Аргументы:
            course (Course): Экземпляр модели Course, к которому будет привязана глава.
            name (str): Название главы.
            order (int): Порядковый номер главы в курсе (используется для сортировки).

        Логика работы:
            1. Инициализирует новый объект модели Chapter.
            2. Устанавливает связь с родительским курсом.
            3. Назначает заголовок и очередность отображения.
            4. Сохраняет запись в базе данных.

        Возвращает:
            Chapter: Созданный и сохраненный объект главы.
        """
    new_chapter = Chapter()
    new_chapter.course = course
    new_chapter.title = name
    new_chapter.order = order
    new_chapter.save()
    return new_chapter


def generate_theory(chapter_name: str, technology: str) -> list:
    """
        Генерирует структурированный учебный контент (теорию) с помощью искусственного интеллекта.

        Функция формирует подробный промпт для языковой модели, отправляет запрос
        и преобразует полученный текстовый ответ в формат Python-списка.

        Аргументы:
            chapter_name (str): Название главы курса (например, "Декораторы в Python").
            technology (str): Изучаемая технология или язык программирования (например, "Python").

        Логика работы:
            1. Формирует системную инструкцию (prompt), описывающую роль ИИ, требования к контенту и формату.
            2. Устанавливает строгие правила форматирования: 5–8 блоков, использование HTML/Bootstrap,
               отсутствие спецсимволов (\n, \t) и строгий JSON-формат.
            3. Объединяет промпт, глобальные правила стилей (STYLE_RULES) и входные параметры.
            4. Вызывает внешнюю функцию `chat(question)` для получения ответа от нейросети.
            5. Десериализует строку ответа в список словарей с помощью `json.loads`.

        Возвращает:
            list: Список словарей, где каждый словарь содержит ключи:
                - "title": Заголовок теоретического блока.
                - "content": Текст блока с HTML-разметкой и Bootstrap-стилями.

        Исключения:
            json.JSONDecodeError: Может возникнуть, если ИИ вернул некорректный JSON или лишний текст.
        """
    prompt = """
    Ты - профессиональный преподаватель и эксперт по созданию учебных материалов по программированию.

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

    1)Верни ответ строго в формате JSON без дополнительного текста. 
    Используй ТОЛЬКО двойные кавычки " для JSON. 
    Экранируй кавычки внутри HTML: используй &quot; или \\\". 
    Не добавляй пояснений, только JSON.
    2)Используй html тэги и bootstrap стили внутри полей "content".
    3)Весь текст на русском языке.
    4)Содержание должно быть точным, структурированным и педагогически продуманным.
    5)Избегай чрезмерно сложного жаргона, если это не обязательно для темы.
    6)Не создавай задачи внутри полей "content".
    7)Не используй классы меняющие цвет заднего фона на светлый
    8)Не используй символы табуляции, например "\\n" или "\\t"
    """

    question = prompt + STYLE_RULES + "\n Название главы:" + chapter_name + ", Название технологии:" + technology
    answer = chat(question)
    return json.loads(answer)


@require_http_methods(["POST"])
def generate_tasks(request) -> JsonResponse:
    """
        Интеллектуальный генератор практических задач на основе теоретического блока.

        Функция использует AI для создания уникального задания, которое закрепляет
        конкретную теорию, автоматически создаёт тесты и обновляет данные в БД.

        Аргументы:
            request (HttpRequest): Объект запроса, содержащий JSON:
                - technology (str): Язык или стек технологий (например, 'Python', 'JS').
                - theory (int/str): ID объекта Theory, по которому генерируется задача.
                - task (int/str): ID объекта Task, в который будут записаны данные.

        Логика работы:
            1. Извлечение контекста: Получает объекты теории и задачи. Очищает старые тесты,
               если задача уже была сгенерирована ранее (флаг is_generated).
            2. Формирование запроса к AI: Создает сложный промпт, включающий очищенный
               от HTML-тегов текст теории и строгие требования к формату (JSON, Bootstrap-стили).
            3. Обработка ответа: Парсит JSON-ответ от нейросети, который должен содержать
               текст задачи и массив тестовых случаев.
            4. Сохранение данных:
               - Обновляет поля объекта Task (заголовок, содержание, форматы ввода/вывода).
               - Создает записи в таблице Test для автоматической проверки кода в будущем.
            5. Ответ клиенту: Формирует JSON с данными новой задачи и списком тестов для UI.

        Контекст JSON-ответа:
            - task_title (str): Название задачи.
            - task_text (str): Условие (HTML/Bootstrap).
            - input_data (str): Описание формата ввода.
            - output_data (str): Описание ожидаемого вывода.
            - tests (list): Список словарей с примерами [вход, выход].

        Возвращает:
            JsonResponse: Данные для динамического обновления страницы курса.
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
    - Обязательно напиши 4 примера входа/выхода.
    - Задача должна решаться в одном файле(например, в index.html, script.js или main.py — в зависимости от языка). 
    Без необходимости создавать несколько файлов, папок, импортировать локальные модули или читать/писать файлы на диск.
    - Входные данные — всегда простые: либо ввод с клавиатуры (prompt, input(), stdin), либо готовый массив/объект прямо в коде. 
    Запрещены: чтение из файлов, сложный парсинг строк, ввод через аргументы командной строки.
    - Выходные данные — вывод в консоль (console.log, print) или на HTML-страницу (если это фронтенд-задача)."""

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
    9)Не пиши такой текст который будет вызывать ошибку JSON.parse в javascript
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
    question = STYLE_RULES + request.GET.get("question", "")
    context = {"answer": chat(question)}
    return JsonResponse(context)


def profile(request, username):
    """
        Отображает страницу профиля пользователя и обрабатывает обновление данных профиля.

        Аргументы:
            request (HttpRequest): Объект запроса Django.
            username (str): Имя пользователя, профиль которого запрашивается.

        Логика работы:
            1. Извлекает целевого пользователя по 'username' или возвращает 404.
            2. Получает или создает объект Profile для ТЕКУЩЕГО авторизованного пользователя.
            3. Считает количество задач текущего пользователя со статусом 'decided=True'.
            4. Если метод POST: валидирует и сохраняет форму ProfileUpdateForm для текущего пользователя.
            5. Если метод GET: инициализирует форму текущими данными профиля.

        Контекст шаблона:
            profile_user (User): Объект пользователя, чья страница просматривается.
            form (ProfileUpdateForm): Форма редактирования профиля авторизованного пользователя.
            count_of_decided_tasks (int): Количество решенных задач авторизованным пользователем.

        Возвращает:
            HttpResponse: Отрисованный шаблон "profile.html".
        """
    user = get_object_or_404(User, username=username)
    profile_instance, created = Profile.objects.get_or_create(user=request.user)
    count_of_decided_tasks = Task.objects.filter(user=request.user, decided=True).count()

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)
        if form.is_valid():
            form.save()
            return redirect("profile", username=username)
    else:
        form = ProfileUpdateForm(instance=profile_instance)

    context = {"profile_user": user, "form": form, "count_of_decided_tasks": count_of_decided_tasks}
    return render(request, "profile.html", context)


def user_login(request):
    """
        Обрабатывает аутентификацию пользователей и вход в систему.

        Аргументы:
            request (HttpRequest): Объект запроса Django.

        Логика работы:
            1. Инициализирует пустой контекст.
            2. При POST-запросе:
               - Проверяет валидность данных формы LoginForm.
               - Пытается аутентифицировать пользователя через стандартный механизм Django.
               - При успешной проверке: осуществляет вход (создание сессии) и перенаправляет на 'home'.
               - При ошибке (неверные данные или невалидная форма): добавляет сообщение об ошибке в контекст.
            3. При GET-запросе или неудачном входе:
               - Создает чистый экземпляр формы LoginForm.
            4. Отрисовывает шаблон "login.html" с формой и (возможно) текстом ошибки.

        Контекст шаблона:
            form (LoginForm): Форма для ввода учетных данных.
            error (str, optional): Сообщение о неудачной попытке входа.

        Возвращает:
            HttpResponse: Страница входа или перенаправление на главную.
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
        Завершает текущую сессию пользователя и выполняет выход из системы.

        Аргументы:
            request (HttpRequest): Объект запроса Django.

        Логика работы:
            1. Вызывает стандартную функцию Django `logout()`, которая удаляет ID пользователя
               из текущей сессии и очищает данные сессии.
            2. После успешного выхода перенаправляет пользователя на страницу входа.

        Возвращает:
            HttpResponseRedirect: Перенаправление на именованный URL-адрес 'login'.
        """
    logout(request)
    return redirect("login")


def registration(request):
    """
       Обрабатывает регистрацию новых пользователей.

       Аргументы:
           request (HttpRequest): Объект запроса Django.

       Логика работы:
           1. Инициализирует пустой контекст.
           2. При POST-запросе:
              - Создает экземпляр формы RegisterForm с данными из запроса.
              - Если форма валидна:
                - Сохраняет нового пользователя в базе данных.
                - Вызывает функцию 'user_login' (авторизация сразу после регистрации).
                - Перенаправляет пользователя на главную страницу ('home').
           3. При GET-запросе (или если форма невалидна):
              - Инициализирует пустую форму RegisterForm.
              - Отрисовывает шаблон 'registration.html'.

       Контекст шаблона:
           form (RegisterForm): Форма регистрации для ввода данных пользователя.

       Возвращает:
           HttpResponse: Страница регистрации или перенаправление после успеха.
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
        Отображает страницу конкретного урока (задачи) в рамках курса и главы.
        Управляет состоянием прогресса пользователя и синхронизирует данные задачи.

        Аргументы:
            request (HttpRequest): Объект запроса Django. Требуется авторизация.
            course_id (int): Идентификатор курса.
            chapter_id (int): Порядковый номер (поле 'order') главы.
            task_id (int): Порядковый номер (поле 'order') теории/задачи внутри главы.

        Логика работы:
            1. Извлекает курс, обновляет в базе текущую главу для этого курса.
            2. Извлекает главу по номеру порядка и обновляет в ней номер текущей задачи.
            3. Выполняет очистку данных: удаляет дубликаты блоков теории, если у них совпадает 'order'.
            4. Работа с контентом:
               - Получает блок теории (Theory) по номеру порядка.
               - Пытается найти существующую задачу (Task) для текущего пользователя.
               - Если задачи нет — создает новую (автоматическая генерация привязки к пользователю).
            5. Работа с попытками:
               - Извлекает все попытки решения (Attempt) текущей задачи.
               - Формирует JSON-строку из последних 5 попыток для отображения в интерфейсе.
            6. Прогресс: вызывает функцию `update_course_progress` для пересчета успеваемости.

        Контекст шаблона:
            course (Course): Объект текущего курса.
            chapters (QuerySet): Список всех глав курса для навигации.
            chapter (Chapter): Текущая активная глава.
            theory_blocks (QuerySet): Все блоки теории в главе.
            theory (Theory): Текущий блок теории.
            task (Task): Объект задачи пользователя, привязанный к теории.
            tests (QuerySet): Тестовые данные для проверки задачи.
            attempts (str): JSON-список с историей последних попыток.
            last_attempt (Attempt): Самая свежая попытка решения.

        Возвращает:
            HttpResponse: Отрисованный шаблон "course_page.html".
        """
    course = get_object_or_404(Course, id=course_id)
    course.current_chapter_number = chapter_id
    course.save()
    chapters = Chapter.objects.filter(course=course)
    chapter = Chapter.objects.get(course=course, order=chapter_id)
    chapter.current_task_number = task_id
    chapter.save()
    theory_blocks = Theory.objects.filter(chapter=chapter)
    for i in range(len(theory_blocks)):
        theory_same_order = Theory.objects.filter(chapter=chapter, order=task_id)
        if len(theory_same_order) > 1:
            for t in theory_same_order[1:]:
                t.delete()
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
    last_attempt = None
    code = ""
    if task:
        try:
            attempts = Attempt.objects.filter(task=task)
            last_attempt = attempts.first()
            attempts = json.dumps(list(attempts[:5].values()), default=str)
        except ObjectDoesNotExist:
            attempts = []
    update_course_progress(course, request.user)
    context = {
        "course": course,
        "chapters": chapters,
        "chapter": chapter,
        "theory_blocks": theory_blocks,
        "theory": theory,
        "task": task,
        "tests": tests,
        "attempts": attempts,
        "last_attempt": last_attempt,
    }
    return render(request, "course_page.html", context)


@require_http_methods(["POST"])
def run_code(request):
    """
        Выполняет произвольный Python-код, полученный через POST-запрос, в изолированном процессе.

        Аргументы:
            request (HttpRequest): Объект запроса Django. Ожидает JSON в теле запроса.
                - code (str): Исходный код на Python для выполнения.
                - input_data (str): Входные данные, передаваемые в стандартный ввод (stdin).

        Логика работы:
            1. Десериализует JSON из тела запроса.
            2. Запускает код через системный вызов `subprocess.run` с использованием интерпретатора python.
            3. Устанавливает лимит времени выполнения (timeout) в 5 секунд для предотвращения зависания сервера.
            4. Перехватывает вывод (stdout) и ошибки (stderr).
            5. Если выполнение прошло успешно, возвращает стандартный вывод.
            6. Если возникла ошибка компиляции или выполнения, возвращает stderr, обернутый в HTML-тег для стилизации.

        Возвращает:
            JsonResponse:
                - {"output": "результат"} в случае успеха или ошибки в коде.
                - {"error": "текст ошибки"} в случае превышения лимита времени или системного сбоя.

        Ограничения безопасности:
            - Код выполняется с правами пользователя, запустившего веб-сервер.
            - Отсутствует изоляция файловой системы и сетевых ресурсов (sandbox).
        """
    request_body = json.loads(request.body)
    code = request_body.get("code")
    input_data = request_body.get("input_data")
    code_timeout = 5
    try:
        process = subprocess.run(
            ["python", "-c", code], input=input_data, capture_output=True, text=True, timeout=code_timeout
        )
        if process.stdout:
            output = process.stdout
        else:
            output = '<div style="color: #dc3545;">' + process.stderr + "</div>"
        return JsonResponse({"output": output})
    except subprocess.TimeoutExpired:
        return JsonResponse({"error": f"Превышено время выполнения программы ({code_timeout} секунд)"})
    except Exception as e:
        return JsonResponse({"error": str(e)})


@require_http_methods(["POST"])
def check_code(request):
    """
        Проверяет решение задачи, создаёт запись о попытке и обновляет прогресс пользователя.

        Аргументы:
            request (HttpRequest): Объект запроса, содержащий JSON:
                - source_code (str): Исходный код решения.
                - task_id (int): Идентификатор проверяемой задачи.
                - course_id (int): Идентификатор курса для обновления прогресса.

        Логика работы:
            1. Извлекает данные из тела запроса (код, ID задачи и курса).
            2. Создает объект Attempt (попытка) в базе данных, привязывая его к пользователю и задаче.
            3. Вызывает функцию `check_attempt(attempt)` (предположительно, запуск тестов и сравнение вывода).
            4. Если проверка пройдена (`attempt.passed == True`):
               - Отмечает задачу как решенную (`decided = True`).
               - Вызывает `update_course_progress` для пересчета общего процента прохождения курса.
            5. Извлекает историю последних 5 попыток по данной задаче.

        Возвращает:
            JsonResponse: Список последних 5 попыток в формате JSON (сериализованный список словарей).
        """
    code = json.loads(request.body)["source_code"]
    task_id = int(json.loads(request.body)["task_id"])
    task = Task.objects.get(id=task_id)
    attempt = Attempt.objects.create(task=task, user=request.user, source_code=code)
    check_attempt(attempt)
    if attempt.passed:
        task.decided = True
        task.save(update_fields=["decided"])
        course_id = json.loads(request.body)["course_id"]
        course = Course.objects.get(id=course_id)
        update_course_progress(course, request.user)
    attempts = Attempt.objects.filter(task=task)
    return JsonResponse({"attempts": json.dumps(list(attempts[:5].values()), default=str)})


def update_course_progress(course, user) -> None:
    """
        Рассчитывает и обновляет общий прогресс пользователя по конкретному курсу.

        Аргументы:
            course (Course): Экземпляр модели курса, для которого считается прогресс.
            user (User): Экземпляр модели пользователя, чей прогресс анализируется.

        Логика расчета:
            1. Прогресс курса складывается из прогресса каждой его главы (Chapter).
            2. Вес каждой главы в курсе равнозначен: 1 / количество_глав.
            3. Прогресс главы определяется как доля решенных задач (Task.decided=True),
               привязанных к блокам теории (Theory) этой главы.
            4. Если задача по конкретной теории решена, к прогрессу главы добавляется
               значение: 1 / количество_блоков_теории_в_главе.
            5. Финальный результат переводится в проценты (0-100) и округляется.

        Действие:
            Обновляет поле 'progress' в объекте 'course' и сохраняет его в базе данных.

        Возвращает:
            None
        """
    progress = 0
    chapters = Chapter.objects.filter(course=course)
    for c in chapters:
        chapter_progress = 0.0
        theory_blocks = Theory.objects.filter(chapter=c)
        for t in theory_blocks:
            if Task.objects.filter(theory=t, user=user).exists():
                task = Task.objects.get(theory=t, user=user)
                if task.decided:
                    chapter_progress += 1 / len(theory_blocks)
        progress += chapter_progress / len(chapters)
    course.progress = round(progress * 100)
    course.save(update_fields=["progress"])


@require_http_methods(["POST"])
def add_new_theory(request):
    """
        Генерирует и сохраняет новые блоки теории для конкретной главы курса.

        Аргументы:
            request (HttpRequest): Объект запроса, содержащий POST-параметры:
                - chapter (int): ID главы, для которой создается теория.
                - course (int): ID курса, к которому относится глава.

        Логика работы:
            1. Извлекает объекты главы и курса из базы данных.
            2. Вызывает внешнюю функцию 'generate_theory' (предположительно ИИ-генератор),
               которая возвращает список словарей с заголовками и контентом.
            3. Сбрасывает указатель текущей задачи главы ('current_theory_number') на 0.
            4. В цикле создает и сохраняет новые объекты 'Theory', устанавливая им
               порядковый номер ('order') согласно индексу в списке.
            5. Обновляет состояние главы в базе данных.
            6. Перенаправляет пользователя на страницу первой созданной задачи курса.

        Возвращает:
            HttpResponseRedirect: Редирект на 'course_page' для просмотра созданного контента.
        """
    chapter_id = int(request.POST.get("chapter"))
    course_id = int(request.POST.get("course"))
    chapter = Chapter.objects.get(id=chapter_id)
    course = Course.objects.get(id=course_id)
    theory_blocks = generate_theory(chapter.title, course.technology)
    chapter.current_theory_number = 0
    for i in range(len(theory_blocks)):
        new_theory = Theory()
        new_theory.chapter = chapter
        new_theory.title = theory_blocks[i]["title"]
        new_theory.text = theory_blocks[i]["content"]
        new_theory.order = i
        new_theory.save()
    chapter.save(update_fields=["current_theory_number"])
    return redirect("course_page", course_id=course_id, chapter_id=chapter.order, task_id=chapter.current_theory_number)
