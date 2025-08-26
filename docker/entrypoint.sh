#!/usr/bin/env bash
set -e

# ждём немного (полезно при работе с внешними БД; для sqlite не критично)
# sleep 1

# Авто-миграции Alembic (если включено)
if [ "${ALEMBIC_AUTOUPGRADE:-1}" = "1" ]; then
  if [ -f "/app/alembic.ini" ] && [ -d "/app/alembic" ]; then
    echo "[entrypoint] Running alembic upgrade head..."
    alembic upgrade head || {
      echo "[entrypoint] alembic upgrade failed"; exit 1;
    }
  else
    echo "[entrypoint] Alembic not found, skipping migrations."
  fi
fi

exec "$@"
