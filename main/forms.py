"""
Django-формы проекта
"""

from django import forms
from main.models import Profile


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма обновления профиля пользователя.

    Предназначена для редактирования данных профиля, привязанного к модели
    ``Profile``. Включает только поле загрузки/изменения аватара.
    Автоматически обрабатывает валидацию файлов и сохранение изменений
    в базе данных через стандартный механизм ``ModelForm``.

    Пример использования::

        def profile_update_view(request):
            profile = request.user.profile
            if request.method == 'POST':
                # Важно передать request.FILES для корректной обработки аватара
                form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Аватар успешно обновлён.")
                    return redirect('profile')
            else:
                form = ProfileUpdateForm(instance=profile)
            return render(request, 'profile/update.html', {'form': form})

    :cvar Meta.model: Модель профиля, связанная с формой.
    :type Meta.model: Profile
    :cvar Meta.fields: Список полей модели, доступных для редактирования.
    :type Meta.fields: list[str]
    """

    class Meta:
        model = Profile
        fields = ['avatar']
