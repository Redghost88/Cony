from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class LoginForm(forms.Form):
    model = User
    username = forms.CharField(label="Логин", max_length=256)
    password = forms.CharField(label="Пароль", max_length=256, widget=forms.PasswordInput)


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email"]
