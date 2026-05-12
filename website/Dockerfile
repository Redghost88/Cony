FROM python:3.12-slim
RUN groupadd -r groupDjango && useradd -r -g groupDjango userDjango

RUN pip install --upgrade pip

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER userDjango