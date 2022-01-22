#!/bin/sh
PATH=$PATH:/home/ubuntu/.local/bin
poetry install
exec poetry run python3 ./bot.py
