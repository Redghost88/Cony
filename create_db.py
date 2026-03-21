import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cony.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import Course, Chapter, Task

# Создаём пользователей
alice = User.objects.create_user(username='alice', email='alice@example.com', password='alicepass')
bob = User.objects.create_user(username='bob', email='bob@example.com', password='bobpass')

# Курс
course = Course.objects.create(
    title="Курс Python",
    author=alice,
    created_at=timezone.now()
)

# Главы
chapter1 = Chapter.objects.create(course=course, title="Переменные")
chapter2 = Chapter.objects.create(course=course, title="Условия")
chapter3 = Chapter.objects.create(course=course, title="Циклы")

# Задачи
Task.objects.create(chapter=chapter1, title="Первые переменные", text=
                    """Создайте переменну a = 5 и выведите ее на экран с помощью print(a)""")
Task.objects.create(chapter=chapter2, title="Условие if", text=
                    """Текст задачи бла бла бла if else все такое""")
Task.objects.create(chapter=chapter3, title="Цикл for", text=
                    """Текст задачи бла бла бла for for range range все такое""")

print("Тестовые данные созданы!")
