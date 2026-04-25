FROM python:3.12-slim
RUN groupadd -r groupDjango && useradd -r -g groupDjango userDjango

RUN pip install --upgrade pip
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
USER userDjango
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]