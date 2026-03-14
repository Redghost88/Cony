from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Course(models.Model):
    """Модель курса"""
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    title = models.CharField(max_length=256, default="Курс")
    created_at = models.DateTimeField(auto_now_add=True)

class Chapter(models.Model):
    """Модель главы"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=256, default="Глава")
    

class Task(models.Model):
    """Модель задачи"""
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    title = models.CharField(max_length=256, default="Задача")
    text = models.CharField(max_length=4096, default="")
    decided = models.BooleanField(default=False)