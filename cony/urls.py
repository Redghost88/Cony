"""
URL configuration for cony project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main.views import logout_view, start_view, start_reasons_view, start_descr_view, start_exp_view, start_aspect_view, \
    start_aspect_frontend_view, start_aspect_backend_view, start_aspect_fullstack_view
from django.contrib.auth import (views as auth_views)

from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path("create_course/", views.create_course, name='create_course'),
    path("generate_answer/", views.generate_answer),
    path('login/', auth_views.LoginView.as_view()),
    path('logout/', logout_view),
    path('start/main', start_view),
    path('start/reasons', start_reasons_view),
    path('start/descr', start_descr_view),
    path('start/exp', start_exp_view),
    path('start/aspect', start_aspect_view),
    path('start/aspect/frontend', start_aspect_frontend_view),
    path('start/aspect/backend', start_aspect_backend_view),
    path('start/aspect/fullstack', start_aspect_fullstack_view),

]
