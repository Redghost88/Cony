"""
Тесты моделей
"""

import pytest
from main.models import Course, Chapter, Theory, Task, Profile, UserStats, Attempt


@pytest.mark.django_db
class TestCourseModel:
    """Тесты модели Course"""

    def test_create_course(self, user):
        """Создание курса"""
        course = Course.objects.create(
            author=user, title="Python Basics", technology="Python"
        )
        assert course.id is not None
        assert course.title == "Python Basics"
        assert course.author == user

    def test_course_str(self, course):
        """Строковое представление"""
        assert str(course) == course.title


@pytest.mark.django_db
class TestChapterModel:
    """Тесты модели Chapter"""

    def test_create_chapter(self, course):
        chapter = Chapter.objects.create(course=course, title="Variables", order=1)
        assert chapter.order == 1
        assert chapter.course == course

    def test_chapter_str(self, chapter):
        assert str(chapter) == chapter.title


@pytest.mark.django_db
class TestTheoryModel:
    """Тесты модели Theory"""

    def test_create_theory(self, chapter):
        theory = Theory.objects.create(
            chapter=chapter,
            title="What is a variable?",
            text="A variable stores data...",
            order=0,
        )
        assert theory.text != ""
        assert theory.order == 0


@pytest.mark.django_db
class TestTaskModel:
    """Тесты модели Task"""

    def test_create_task(self, theory, user):
        task = Task.objects.create(
            theory=theory,
            user=user,
            title="Print Hello",
            task_content="Write code to print Hello",
        )
        assert task.decided is False  # default value
        assert task.is_generated is False

    def test_task_str(self, task):
        assert str(task) == task.title


@pytest.mark.django_db
class TestProfileModel:
    """Тесты модели Profile"""

    def test_create_profile(self, user):
        profile = Profile.objects.create(user=user)
        assert profile.avatar

    def test_profile_str(self, user):
        profile = Profile.objects.create(user=user)
        assert str(profile) == f"Profile of {user.username}"


@pytest.mark.django_db
class TestUserStatsModel:
    """Тесты модели UserStats"""

    def test_create_user_stats(self, user):
        stats = UserStats.objects.create(user=user)
        assert stats.complete_seria == 0
        assert stats.max_seria == 0

    def test_update_seria(self, user):
        stats = UserStats.objects.create(user=user, complete_seria=3)
        stats.complete_seria = 5
        stats.save()
        assert UserStats.objects.get(user=user).complete_seria == 5


@pytest.mark.django_db
class TestAttemptModel:
    """Тесты модели Attempt"""

    def test_create_attempt(self, task, user):
        attempt = Attempt.objects.create(
            task=task, user=user, source_code="print('hello')"
        )
        assert attempt.status == "pending"
        assert attempt.passed is False

    def test_attempt_update_status(self, attempt):
        attempt.status = "finished"
        attempt.passed = True
        attempt.save()
        assert Attempt.objects.get(id=attempt.id).passed is True
