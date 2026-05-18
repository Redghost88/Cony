"""Конфигурация Celery для асинхронных задач проекта."""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cony.settings")
app = Celery("cony")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
