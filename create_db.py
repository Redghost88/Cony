import os
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cony.settings")
django.setup()

from django.contrib.auth.models import User
from main.models import Course, Chapter, Task, Test, Theory

# Создаём пользователей
alice = User.objects.create_user(username="alice", email="alice@example.com", password="alicepass")
bob = User.objects.create_user(username="bob", email="bob@example.com", password="bobpass")

# Курс
course = Course.objects.create(title="Курс Python", author=alice, created_at=timezone.now())

# Главы
chapter1 = Chapter.objects.create(course=course, title="Переменные", order=0)
chapter2 = Chapter.objects.create(course=course, title="Условия", order=1)
chapter3 = Chapter.objects.create(course=course, title="Циклы", order=2)

# Задачи
task1 = Theory.objects.create(
    chapter=chapter1,
    title="Первые переменные",
    text="""Создайте переменну a = 5 и выведите ее на экран с помощью print(a)""",
)
user_task_alice = Task.objects.create(
    theory=task1, user=alice, task_content="вводится число a и b. выведи их сумму", is_generated=True
)
Test.objects.create(task=user_task_alice, input_data="4 5", output_data="9", order=0)
Test.objects.create(task=user_task_alice, input_data="1 3", output_data="4", order=1)
Test.objects.create(task=user_task_alice, input_data="7 0", output_data="7", order=2)
Theory.objects.create(chapter=chapter2, title="Условие if", text="""Текст задачи бла бла бла if else все такое""")
Theory.objects.create(
    chapter=chapter3, title="Цикл for", text="""Текст задачи бла бла бла for for range range все такое"""
)

print("Тестовые данные созданы!")
