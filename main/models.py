"""
Файл отвечает, за модели
"""

from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Course(models.Model):
    """Модель курса обучения.

    Представляет учебный курс, созданный пользователем. Содержит информацию
    об авторе, названии и дате создания курса. Используется для организации
    образовательного контента в системе.

    :ivar author: Ссылка на пользователя-автора курса.
    :type author: ForeignKey to :class:`~django.contrib.auth.models.User`
    :ivar title: Название курса (максимум 256 символов).
    :type title: CharField
    :ivar created_at: Дата и время создания курса (автоматически).
    :type created_at: DateTimeField
    """

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=256, default="Курс")
    technology = models.CharField(max_length=256, default="")
    current_chapter_number = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Chapter(models.Model):
    """Модель главы курса.

    Представляет отдельную главу в рамках учебного курса. Содержит информацию
    о названии главы и связи с родительским курсом. Используется для структурирования
    образовательного контента по разделам.

    :ivar course: Ссылка на родительский курс.
    :type course: ForeignKey to :class:`~courses.models.Course`
    :ivar title: Название главы (максимум 256 символов).
    :type title: CharField
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=256, default="Глава")
    order = models.PositiveSmallIntegerField(default=0)
    current_theory_number = models.IntegerField(default=0)


class Theory(models.Model):
    """Представляет отдельную блок теории в рамках главы учебного курса. Содержит информацию
    о названии, текстовом описании. Используется для организации
    практических заданий и отслеживания прогресса обучения.

    :ivar chapter: Ссылка на родительскую главу.
    :type chapter: ForeignKey to :class:`~courses.models.Chapter`
    :ivar title: Название задачи (максимум 256 символов).
    :type title: CharField
    :ivar text: Текстовое описание задачи (максимум 4096 символов).
    :type text: CharField
    :ivar decided: Статус выполнения задачи (True — выполнено, False — не выполнено).
    :type decided: BooleanField"""

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    title = models.CharField(max_length=256, default="Задача")
    text = models.CharField(max_length=4096, default="")
    order = models.PositiveSmallIntegerField(default=0)


class Task(models.Model):
    """
    Модель задачи, привязанной к пользователю и теоретическому материалу.

    Хранит условие задачи, входные/выходные данные для автоматической проверки,
    статус решения и признак способа создания (ручной или сгенерированный).
    Используется в системе обучения и трекинга прогресса.

    **Поля модели:**

    - ``theory``: Связь с теоретическим блоком (``ForeignKey`` к ``Theory``).
      Задача удаляется каскадно при удалении теории.
    - ``user``: Связь с автором/владельцем задачи (``ForeignKey`` к ``User``).
      Задача удаляется каскадно при удалении пользователя.
    - ``title``: Заголовок задачи. Максимальная длина — 256 символов.
    - ``task_content``: Текст условия задачи. Максимальная длина — 4096 символов,
      может быть ``NULL``.
    - ``input_data``: Строка с примером входных данных для тестирования решения.
    - ``output_data``: Строка с ожидаемым правильным выводом.
    - ``decided``: Флаг успешного решения задачи пользователем (``True``/``False``).
    - ``is_generated``: Флаг, указывающий, была ли задача создана автоматически
      (например, ИИ-генератором) или вручную преподавателем.
    """

    theory = models.ForeignKey(Theory, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=256, default="Задача")
    task_content = models.CharField(max_length=4096, null=True, default="")
    input_data = models.CharField(max_length=4096, default="")
    output_data = models.CharField(max_length=4096, default="")
    decided = models.BooleanField(default=False)
    is_generated = models.BooleanField(default=False)


class Test(models.Model):
    """
    Модель, представляющая отдельный тестовый кейс для автоматической проверки решения задания.

    Хранит входные и ожидаемые выходные данные, а также порядок выполнения теста.
    Используется пайплайном валидации для сравнения фактического вывода пользовательского кода
    с эталонным результатом.

    **Поля модели:**
      - ``task`` (:class:`~django.db.models.ForeignKey`): Ссылка на родительское задание.
        Использует ``on_delete=models.PROTECT``, что **запрещает удаление самого задания**,
        пока существуют связанные с ним тесты (защита от случайной потери тестовой базы).
      - ``input_data`` (:class:`~django.db.models.CharField`): Входные данные теста.
        Максимальная длина — 1024 символа, по умолчанию пустая строка.
      - ``output_data`` (:class:`~django.db.models.CharField`): Ожидаемые выходные данные.
        Максимальная длина — 1024 символа, по умолчанию пустая строка.
      - ``correct`` (:class:`~django.db.models.BooleanField`): Флаг валидности теста.
        Позволяет временно отключать тесты без удаления из БД (по умолчанию ``False``).
      - ``order`` (:class:`~django.db.models.PositiveSmallIntegerField`): Порядковый номер
        теста для детерминированной последовательности запуска (по умолчанию ``0``).

    **Meta-атрибуты:**
      - ``ordering``: Набор тестов по умолчанию сортируется по возрастанию ``order``,
        а при совпадении порядка — по возрастанию ``id``.

    .. note::
       ``on_delete=models.PROTECT`` применяется именно к полям ``Test``, поэтому при попытке
       удалить ``Task`` Django поднимет ``ProtectedError``. Это гарантирует, что задания
       не останутся без тестового покрытия при административных операциях.
    """

    task = models.ForeignKey(Task, on_delete=models.PROTECT)
    input_data = models.CharField(max_length=1024, default="")
    output_data = models.CharField(max_length=1024, default="")
    correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Profile(models.Model):
    """
    Модель профиля пользователя, расширяющая стандартную модель ``User``.

    Предназначена для хранения дополнительных данных пользователя, в частности
    изображения аватара. Профиль связан с учётной записью отношением один-к-одному
    и удаляется автоматически при удалении пользователя (``on_delete=models.CASCADE``).

    **Поля модели:**

    - ``user``: Связь один-к-одному с моделью ``User``.
    - ``avatar``: Поле для загрузки изображения. Файлы сохраняются в директории
      ``avatars/``, по умолчанию используется ``default.jpg``.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to="avatars/", default="default.jpg")


class Attempt(models.Model):
    """
    Модель, хранящая информацию о попытках пользователя решить задание.

    Каждая запись фиксирует отправленный исходный код, результат проверки
    (успешность) и журнал выполнения. Связана с заданием и пользователем
    через каскадное удаление.

    **Поля модели:**
      - ``task`` (:class:`~django.db.models.ForeignKey`): Ссылка на задание.
        При удалении задания все связанные попытки удаляются каскадно.
      - ``user`` (:class:`~django.db.models.ForeignKey`): Ссылка на пользователя.
        При удалении пользователя все его попытки удаляются.
      - ``source_code`` (:class:`~django.db.models.TextField`): Исходный код, отправленный пользователем.
      - ``created_at`` (:class:`~django.db.models.DateTimeField`): Дата и время создания попытки.
        Заполняется автоматически при создании записи (``auto_now_add=True``).
      - ``passed`` (:class:`~django.db.models.BooleanField`): Флаг успешности проверки.
        ``True`` — код прошёл все тесты, ``False`` — нет (по умолчанию ``False``).
      - ``check_log`` (:class:`~django.db.models.TextField`): Журнал выполнения или ошибки компиляции/тестов.
        Может оставаться пустым (``blank=True``).

    **Meta-атрибуты:**
      - ``ordering``: Записи по умолчанию сортируются по убыванию ``created_at``
        (самые новые попытки отображаются первыми).

    .. note::
       Для получения последней попытки пользователя по конкретному заданию
       рекомендуется использовать ``Attempt.objects.filter(task=task, user=user).first()``.
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_code = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    passed = models.BooleanField(default=False)
    check_log = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
