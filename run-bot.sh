#!/bin/sh
poetry install
exec poetry run python3 ./bot.py
