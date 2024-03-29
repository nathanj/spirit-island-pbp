#!/bin/sh
export PYTHONUNBUFFERED=TRUE
PATH=$PATH:/home/ubuntu/.local/bin
poetry install --no-root
poetry run python3 ./manage.py collectstatic --noinput
poetry run python3 ./manage.py migrate
exec poetry run gunicorn island.wsgi
