#!/usr/bin/env bash
set -e

echo "▶️  Entry: wait DB & migrate & run bot"

# подождём базу из DATABASE_URL
if [ -n "$DATABASE_URL" ]; then
python - "$DATABASE_URL" <<'PY'
import os, sys, time, socket
from urllib.parse import urlparse

url = urlparse(sys.argv[1])
host, port = url.hostname or "db", url.port or 5432
print(f"[wait-db] waiting for {host}:{port} ...", flush=True)
for i in range(120):
    try:
        with socket.create_connection((host, int(port)), timeout=1.0):
            print("[wait-db] ok", flush=True)
            break
    except OSError:
        time.sleep(1)
else:
    print("[wait-db] failed", flush=True); sys.exit(1)
PY
fi

# миграции при старте (если ALEMBIC_AUTOUPGRADE включён)
if [ "$ALEMBIC_AUTOUPGRADE" = "1" ] || [ "$ALEMBIC_AUTOUPGRADE" = "true" ]; then
  echo "▶️  alembic upgrade head"
  alembic upgrade head
fi

# запуск бота
echo "▶️  run bot"
exec python -m src.main
