"""
Тесты view функций
"""

import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch
from main.models import UserStats


@pytest.mark.django_db
class TestAuthViews:
    """Тесты аутентификации"""

    def test_home_page_status(self, client):
        """Главная страница доступна анонимно"""
        response = client.get(reverse("home"))
        assert response.status_code == 200
        assert "courses" in response.context

    def test_login_page_get(self, client):
        """Страница входа загружается"""
        response = client.get(reverse("login"))
        assert response.status_code == 200
        assert "form" in response.context

    def test_login_success(self, client, user):
        """Успешный вход"""
        response = client.post(
            reverse("login"), {"username": user.username, "password": "testpass123"}
        )
        assert response.status_code == 302  # redirect
        assert response.url == reverse("home")

    def test_login_wrong_password(self, client, user):
        """Неверный пароль"""
        response = client.post(
            reverse("login"), {"username": user.username, "password": "wrongpass"}
        )
        assert response.status_code == 200
        assert "error" in response.context

    def test_logout(self, authenticated_client):
        """Выход из системы"""
        response = authenticated_client.get(reverse("logout"))
        assert response.status_code == 302
        assert response.url == reverse("login")

    def test_registration_get(self, client):
        """Страница регистрации"""
        response = client.get(reverse("registration"))
        assert response.status_code == 200

    def test_registration_success(self, client):
        """Успешная регистрация"""
        response = client.post(
            reverse("registration"),
            {
                "username": "newuser123",
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        assert response.status_code == 302
        assert User.objects.filter(username="newuser123").exists()


@pytest.mark.django_db
class TestProfileViews:
    """Тесты профиля"""

    def test_profile_page_authenticated(self, authenticated_client, user):
        """Просмотр своего профиля"""
        UserStats.objects.create(user=user)
        response = authenticated_client.get(reverse("profile", args=[user.username]))
        assert response.status_code == 200
        assert "profile_user" in response.context

    def test_profile_page_other_user(self, authenticated_client, user):
        """Просмотр чужого профиля"""
        UserStats.objects.create(user=user)
        other = User.objects.create_user("other", password="pass")
        response = authenticated_client.get(reverse("profile", args=[other.username]))
        assert response.status_code == 200

    def test_profile_update_success(self, authenticated_client, user):
        """Обновление профиля"""
        UserStats.objects.create(user=user)
        response = authenticated_client.post(
            reverse("profile", args=[user.username]), {"avatar": ""}, follow=True
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestCourseViews:
    """Тесты курсов"""

    def test_course_page_authenticated(
        self, authenticated_client, course, chapter, theory
    ):
        """Страница курса"""
        response = authenticated_client.get(
            reverse("course_page", args=[course.id, chapter.order, theory.order])
        )
        assert response.status_code == 200
        assert "course" in response.context

    def test_course_page_redirect_anonymous(self, client, course, chapter, theory):
        """Аноним перенаправляется на вход"""
        response = client.get(
            reverse("course_page", args=[course.id, chapter.order, theory.order])
        )
        assert response.status_code == 302
        assert "login" in response.url

    def test_create_course_get(self, authenticated_client):
        """Форма создания курса"""
        response = authenticated_client.get(reverse("create_course"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestExecutionViews:
    """Тесты выполнения кода"""

    def test_run_code_post_authenticated(self, authenticated_client):
        """Запуск кода"""
        import json

        response = authenticated_client.post(
            reverse("run_code"),
            data=json.dumps({"code": 'print("hello")', "input_data": ""}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "output" in response.json() or "error" in response.json()

    @patch("main.views.execution_views.send_attempt.delay")
    def test_check_code_post_authenticated(
        self, mock_send_attempt, authenticated_client, task
    ):
        """Создание попытки"""
        import json

        response = authenticated_client.post(
            reverse("check_code"),
            data=json.dumps(
                {
                    "source_code": 'print("test")',
                    "task_id": task.id,
                    "course_id": task.theory.chapter.course.id,
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "attempts" in response.json()

    def test_get_attempt_status(self, authenticated_client, attempt):
        """Получение статуса попытки"""
        response = authenticated_client.get(
            reverse("get_attempt_status", args=[attempt.id])
        )
        assert response.status_code == 200
        assert "status" in response.json()
