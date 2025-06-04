# FROM python:3.11.9-alpine
FROM python:3.11-slim-bullseye

#ENV PYTHONPATH=/
WORKDIR /

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
    # Установка unrar и john больше не нужна, если пробрасываем через volumes
    # RUN apk update && apk add --no-cache unrar-free john # Для Alpine
    # RUN apt-get update && apt-get install -y unrar john # Для Debian/Ubuntu

# Создаем директорию для временных файлов внутри контейнера и даем права
RUN mkdir -p /app/temp_files && chmod -R 777 /app/temp_files

COPY . . 

ENV PYTHONPATH=/app
VOLUME /app/temp_files

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
# COPY . 3lab/app/celery/tasks.py

# если в docker-compose есть, следующую строку оставь закомментированной.
# CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]