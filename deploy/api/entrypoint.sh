#!/bin/sh
set -eu

python - <<'PY'
import asyncio

import asyncpg

from src.core.config import get_settings


async def wait_for_database() -> None:
    postgres = get_settings().postgres
    for attempt in range(1, 31):
        try:
            connection = await asyncpg.connect(
                host=postgres.host,
                port=postgres.port,
                user=postgres.user,
                password=postgres.password,
                database=postgres.db,
                timeout=2,
            )
            await connection.close()
            print("Database is ready", flush=True)
            return
        except Exception as exc:
            if attempt == 30:
                raise RuntimeError("Database did not become ready within 60 seconds") from exc
            print(f"Waiting for database ({attempt}/30): {exc}", flush=True)
            await asyncio.sleep(2)


asyncio.run(wait_for_database())
PY

echo "Running database migrations"
alembic upgrade head
echo "Database migrations completed"

exec "$@"
