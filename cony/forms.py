"""
Django-формы проекта
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class LoginForm(forms.Form):
    """
    Форма авторизации пользователя.

    Предназначена для валидации учётных данных при входе в систему.
    Содержит поля логина и пароля с ограничениями длины и соответствующими
    виджетами отображения.

    Пример использования::

        def login_view(request):
            if request.method == 'POST':
                form = LoginForm(request.POST)
                if form.is_valid():
                    # аутентификация и редирект
                    ...

    :cvar model: Модель пользователя, связанная с формой. Используется как
                 справочное поле, так как форма наследуется от ``forms.Form``,
                 а не от ``ModelForm``.
    :type model: User
    :cvar username: Поле ввода логина.
    :type username: django.forms.CharField
    :cvar password: Поле ввода пароля с маскированием символов.
    :type password: django.forms.CharField
    """

    model = User
    username = forms.CharField(label="Логин", max_length=256)
    password = forms.CharField(label="Пароль", max_length=256, widget=forms.PasswordInput)


class RegisterForm(UserCreationForm):
    """
    Форма регистрации нового пользователя.

    Наследуется от ``django.contrib.auth.forms.UserCreationForm`` и автоматически
    добавляет поля для ввода и подтверждения пароля (``password1`` и ``password2``).
    В ``Meta`` указаны модель пользователя и дополнительные поля, которые будут
    отображаться в форме.

    Пример использования::

        def register_view(request):
            if request.method == 'POST':
                form = RegisterForm(request.POST)
                if form.is_valid():
                    user = form.save()
                    # логика после успешной регистрации (авторизация, email-подтверждение и т.д.)
                    ...

    :cvar Meta.model: Модель пользователя, привязанная к форме.
    :type Meta.model: User
    :cvar Meta.fields: Список полей модели, включаемых в форму. Парольные поля
                       наследуются автоматически и не требуют явного указания.
    :type Meta.fields: list[str]
    """

    class Meta:
        model = User
        fields = ["username", "email"]
