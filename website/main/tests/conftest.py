"""
Заготовки для текстов
"""

import pytest
from django.contrib.auth.models import User
from main.models import Attempt, Course, Chapter, Theory, Task
from factory.django import DjangoModelFactory
from factory import Faker, Sequence, SubFactory
from factory import post_generation

from cony import settings


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = Sequence(lambda n: f"testuser{n}")
    email = Faker("email")

    @post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        raw_password = extracted or "testpass123"
        self.set_password(raw_password)


class CourseFactory(DjangoModelFactory):
    class Meta:
        model = Course

    title = Sequence(lambda n: f"Test Course {n}")
    technology = Faker("word")
    author = SubFactory(UserFactory)


class ChapterFactory(DjangoModelFactory):
    class Meta:
        model = Chapter

    title = Sequence(lambda n: f"Chapter {n}")
    course = SubFactory(CourseFactory)
    order = Sequence(lambda n: n)


class TheoryFactory(DjangoModelFactory):
    class Meta:
        model = Theory

    title = Sequence(lambda n: f"Theory {n}")
    text = Faker("text", max_nb_chars=200)
    chapter = SubFactory(ChapterFactory)
    order = Sequence(lambda n: n)


class TaskFactory(DjangoModelFactory):
    class Meta:
        model = Task

    title = Sequence(lambda n: f"Task {n}")
    task_content = Faker("text", max_nb_chars=300)
    theory = SubFactory(TheoryFactory)
    user = SubFactory(UserFactory)


@pytest.fixture(autouse=True)
def use_sqlite_for_tests(db):
    """Переключает БД на SQLite только для тестов"""
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # или "test_db.sqlite3" для файловой БД
    }


@pytest.fixture
def user(db):
    return UserFactory.create(password="testpass123")


@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def course(db, user):
    return CourseFactory.create(author=user)


@pytest.fixture
def chapter(db, course):
    return ChapterFactory.create(course=course)


@pytest.fixture
def theory(db, chapter):
    return TheoryFactory.create(chapter=chapter)


@pytest.fixture
def task(db, theory, user):
    return TaskFactory.create(theory=theory, user=user)


@pytest.fixture
def attempt(db, task, user):
    """Создает тестовую попытку решения задачи"""
    return Attempt.objects.create(
        task=task,
        user=user,
        source_code="print('hello')",
        status="pending",
        passed=False,
    )
