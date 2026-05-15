# Проект "Cony"

### Инструкция по настройке проекта:
1. Склонировать проект
2. Открыть проект в PyCharm с наcтройками по умолчанию
3. Создать виртуальное окружение (через settings -> project "cony" -> project interpreter)
4. Открыть терминал в PyCharm, проверить, что виртуальное окружение активировано.
5. Создать свой ключ от нейросети: 
   - открыть сайт https://openrouter.ai/
   - нажать "Get api key"
   - нажать "Create"
   - копируете ключ и вставляете его в поле OPENROUTER_KEY файла .env
6. Обновить pip:
   ```bash
   sudo apt install python3-venv
   ```
7. Запустить докер образы
   ```bash
   docker compose up --build -d 
   ```
8. Синхронизировать структуру базы данных и статики: 
   ```bash
   docker compose exec cony python manage.py migrate
   docker compose run --rm cony python manage.py migrate django_celery_results
   docker compose exec cony python manage.py collectstatic --noinput   
   ```