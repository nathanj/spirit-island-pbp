#!/bin/sh
export PYTHONUNBUFFERED=TRUE
PATH=/home/si/.local/bin:$PATH
uv self version
uv sync --no-dev --group redis
uv run --no-dev --locked ./manage.py collectstatic --noinput
uv run --no-dev --locked ./manage.py migrate
exec uv run --no-dev --locked gunicorn island.wsgi
