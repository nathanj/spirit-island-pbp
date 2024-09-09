#!/bin/sh
export PYTHONUNBUFFERED=TRUE
PATH=/home/si/.local/bin:$PATH
poetry --version
poetry install --no-root
exec poetry run python3 ./bot.py
