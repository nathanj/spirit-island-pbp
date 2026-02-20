#!/bin/sh
export PYTHONUNBUFFERED=TRUE
PATH=/home/si/.local/bin:$PATH
uv self version
uv sync --no-dev --group redis
exec uv run --no-dev --locked python3 ./bot.py
