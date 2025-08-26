FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# системные утилиты для сборки некоторых пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# отдельный venv внутри образа
RUN python -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# ставим зависимости
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# код
COPY src ./src
COPY alembic.ini ./alembic.ini
# migrations могут отсутствовать — копируем, если есть
# если у тебя есть папка migrations — раскомментируй следующую строку
# COPY migrations ./migrations

# на запуск — python из venv
CMD ["python", "-m", "src.main"]
