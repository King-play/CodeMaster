#!/bin/sh
set -e

python -m alembic upgrade head
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}"

