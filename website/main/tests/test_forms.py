"""
Тесты форм
"""

import pytest
from main.forms import ProfileUpdateForm, LoginForm, RegisterForm
from main.models import Profile


@pytest.mark.django_db
class TestProfileUpdateForm:
    """Тесты формы профиля"""

    def test_valid_profile_form(self, user):
        """Валидные данные"""
        Profile.objects.create(user=user)
        form = ProfileUpdateForm(data={}, instance=user.profile)
        assert form.is_valid()

    def test_profile_form_empty_bio(self, user):
        """Пустая биография допустима"""
        Profile.objects.create(user=user)
        form = ProfileUpdateForm(data={}, instance=user.profile)
        assert form.is_valid()


@pytest.mark.django_db
class TestLoginForm:
    """Тесты формы входа"""

    def test_valid_login_form(self):
        """Валидные данные"""
        form = LoginForm(data={"username": "test", "password": "pass123"})
        assert form.is_valid()

    def test_login_form_missing_username(self):
        """Нет username"""
        form = LoginForm(data={"password": "pass123"})
        assert not form.is_valid()
        assert "username" in form.errors

    def test_login_form_missing_password(self):
        """Нет password"""
        form = LoginForm(data={"username": "test"})
        assert not form.is_valid()
        assert "password" in form.errors


@pytest.mark.django_db
class TestRegisterForm:
    """Тесты формы регистрации"""

    def test_valid_register_form(self):
        """Валидная регистрация"""
        form = RegisterForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )
        assert form.is_valid()

    def test_register_passwords_mismatch(self):
        """Пароли не совпадают"""
        form = RegisterForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Pass123!",
                "password2": "DifferentPass!",
            }
        )
        assert not form.is_valid()
        assert "password2" in form.errors or "__all__" in form.errors

    def test_register_weak_password(self):
        """Слабый пароль"""
        form = RegisterForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "123",
                "password2": "123",
            }
        )
        assert not form.is_valid()
