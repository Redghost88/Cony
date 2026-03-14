"""
Файл отвечает, цитата "за модели"
"""
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Course(models.Model):
    """    Модель курса обучения.

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
    created_at = models.DateTimeField(auto_now_add=True)

class Chapter(models.Model):
    """    Модель главы курса.

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
    

class Task(models.Model):
    """    Представляет отдельную задачу в рамках главы учебного курса. Содержит информацию
    о названии, текстовом описании и статусе выполнения. Используется для организации
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
    decided = models.BooleanField(default=False)