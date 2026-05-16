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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from main.views import ai_views, auth_views, course_views, execution_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", course_views.home, name="home"),
    path("create_course/", course_views.create_course, name="create_course"),
    path("generate_answer/", ai_views.generate_answer),
    path("profile/<str:username>", auth_views.profile, name="profile"),
    path("login/", auth_views.user_login, name="login"),
    path("logout/", auth_views.user_logout),
    path("registration/", auth_views.registration, name="registration"),
    path(
        "course/<int:course_id>/chapter/<int:chapter_id>/task/<int:task_id>",
        course_views.course_page,
        name="course_page",
    ),
    path("run_code/", execution_views.run_code),
    path("send_code/", execution_views.check_code),
    path("generate_task/", ai_views.generate_tasks),
    path("generate_course/", ai_views.generate_course),
    path("generate_chat_answer/", ai_views.generate_chat_answer),
    path("add_new_theory/", course_views.add_new_theory),
    path("attempt_status/<int:attempt_id>/", execution_views.get_attempt_status),
    path("get_attempts/<int:task_id>/", execution_views.get_task_attempts),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
