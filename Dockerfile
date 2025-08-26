FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Bishkek

# Базовые инструменты (минимум)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Зависимости
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Проект
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

# Точка входа
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
