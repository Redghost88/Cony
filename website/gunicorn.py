from os import environ, cpu_count, name


def max_workers():
    return cpu_count()

bind = "0.0.0.0:8000"
max_requests = 1000
worker_class = "gevent"
workers = max_workers()

env = {
    "DJANGO_SETTINGS_MODULE": "website.settings",
}

reload = True
name = "website"