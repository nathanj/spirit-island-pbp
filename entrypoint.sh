#!/bin/sh
export PYTHONUNBUFFERED=TRUE
# ensure root user is created using env vars
poetry run python3 ./manage.py createsuperuser --no-input || true
poetry --version
poetry install --no-root
poetry run python3 ./manage.py collectstatic --noinput
poetry run python3 ./manage.py migrate
poetry run python3 ./manage.py runserver 0.0.0.0:8000
