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
    progress = models.PositiveSmallIntegerField(default=0)
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
        Модель для хранения практических задач, привязанных к учебному курсу и пользователю.

        Поля:
            theory (ForeignKey): Связь с моделью Theory. Определяет, к какому теоретическому
                блоку относится данная задача. При удалении теории задача удаляется (CASCADE).
            user (ForeignKey): Связь с моделью User. Указывает на владельца/автора задачи
                или пользователя, для которого эта задача была сгенерирована.
            title (CharField): Краткое название задачи. По умолчанию — "Задача".
            task_content (CharField): Подробное описание условия задачи (поддерживает до 4096 символов).
            input_data (CharField): Описание формата входных данных или сами входные данные.
            output_data (CharField): Описание ожидаемого результата или эталонный вывод.
            decided (BooleanField): Флаг состояния. Принимает значение True, если пользователь
                успешно решил задачу.
            is_generated (BooleanField): Указывает, была ли задача создана автоматически
                нейросетью (True) или добавлена вручную (False).

        Особенности:
            - Модель используется для индивидуального отслеживания прогресса пользователя
              по конкретным темам.
            - Поле 'is_generated' позволяет системе отличать базовый контент от
              динамически созданного ИИ.
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
        Модель для хранения набора тестовых случаев (test cases),
        используемых для автоматической валидации решений практических задач.

        Поля:
            task (ForeignKey): Ссылка на задачу (Task), к которой относится данный тест.
                Используется режим PROTECT, предотвращающий удаление задачи,
                если к ней привязаны активные тесты.
            input_data (CharField): Входные аргументы или данные, которые будут
                переданы в стандартный поток ввода (stdin) проверяемой программы.
            output_data (CharField): Эталонный результат (строка), с которым
                сравнивается вывод программы пользователя для определения успешности теста.
            correct (BooleanField): Служебный флаг. В текущей логике может использоваться
                для быстрой фильтрации "эталонных" тестов.
            order (PositiveSmallIntegerField): Порядковый номер теста в списке.
                Позволяет отображать тесты (например, примеры в условии) в строгой последовательности.

        Роль в системе:
            Модель обеспечивает работу модуля проверки кода (например, в функции 'check_attempt').
            Каждый объект представляет собой пару "Вход -> Ожидаемый выход".
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
        Модель профиля пользователя, расширяющая стандартную модель User дополнительными полями.

        Используется для хранения метаданных пользователя, которые не входят в
        базовый набор полей аутентификации Django.

        Поля:
            user (OneToOneField): Связь "один-к-одному" с системной моделью User.
                При удалении пользователя связанный профиль удаляется автоматически (CASCADE).
            avatar (ImageField): Изображение пользователя (аватар).
                - Файлы загружаются в подпапку 'avatars/'.
                - Если изображение не загружено, используется 'default.jpg'.

        Особенности:
            - Позволяет связывать прогресс обучения и личные настройки с конкретным аккаунтом.
            - Для корректной работы ImageField требуется установленная библиотека Pillow.
        """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to="avatars/", default="default.jpg")


class Attempt(models.Model):
    """
        Модель для хранения попыток решения задач пользователями.

        Каждая запись фиксирует состояние кода в момент отправки на проверку
        и сохраняет результат тестирования.

        Поля:
            task (ForeignKey): Ссылка на задачу (Task), к которой относится попытка.
                При удалении задачи все связанные попытки удаляются (CASCADE).
            user (ForeignKey): Ссылка на пользователя (User), совершившего попытку.
                При удалении пользователя его история попыток удаляется (CASCADE).
            source_code (TextField): Полный текст программного кода, который был
                отправлен пользователем на проверку.
            created_at (DateTimeField): Дата и время создания попытки.
                Устанавливается автоматически в момент сохранения записи (auto_now_add).
            passed (BooleanField): Статус успешности. Устанавливается в True,
                если код успешно прошел все тесты в рамках данной попытки.
            check_log (TextField): Технический лог проверки. Сюда записываются ошибки
                компиляции, результаты сравнения тестов или сообщения от интерпретатора.

        Особенности:
            - Позволяет анализировать историю прогресса пользователя.
            - Хранит хронологию изменений кода, что полезно для отладки и предотвращения списывания.
        """
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_code = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    passed = models.BooleanField(default=False)
    check_log = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class UserStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    complete_seria = models.IntegerField(default=0)
    max_seria = models.IntegerField(default=0)
    last_task_complete_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.max_seria = max(self.complete_seria, self.max_seria)

        update_fields = kwargs.get("update_fields", None)
        if update_fields is not None and "complete_seria" in update_fields:
            if "max_seria" not in update_fields:
                update_fields = set(update_fields)
                update_fields.add("max_seria")
                kwargs["update_fields"] = list(update_fields)

        super().save(*args, **kwargs)
