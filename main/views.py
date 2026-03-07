import uuid
import requests
from django.shortcuts import render
from gigachat import GigaChat
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User

from main.forms import ProfileUpdateForm
from main.models import Profile


#from cony.settings import GIGACHAT_AUTH_TOKEN

# Create your views here.

def home(request):
    return render(request, 'index.html')

def create_course(request):
    context = {}
    giga = GigaChat(
        credentials="aboba"
    )

    response = giga.chat("Напиши 10 тем для изучения в питоне кратко")

    context["answer"] = response.choices[0].message.content
    return render(request, 'create_course.html', context)

def profile(request, username):
    user = get_object_or_404(User, username=username)
    profile_instance, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)
        if form.is_valid():
            form.save()
            return redirect('profile', username=username)
    else:
        form = ProfileUpdateForm(instance=profile_instance)

    context = {
        "profile_user": user,
        "form": form,
    }
    return render(request, "profile.html", context)