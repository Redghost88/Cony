"""
Настройки gunicorn
"""

from os import cpu_count


def max_workers():
    return cpu_count()


bind = "0.0.0.0:8000"
max_requests = 1000
timeout = 300
worker_class = "gthread"
threads = 4
workers = max_workers()


env = {
    "DJANGO_SETTINGS_MODULE": "website.settings",
}

reload = True
name = "website"
