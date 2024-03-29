# Spirit Island PBP Helper

A website to assist playing Spirit Island over discord in the play by post section.

## Running locally

Copy `.env.template` to `.env` and fill in the variables

```
poetry install
poetry run ./manage.py migrate auth
poetry run ./manage.py migrate pbf 0001
poetry run ./manage.py seeddb
poetry run ./manage.py migrate
poetry run ./manage.py collectstatic
poetry run ./manage.py runserver
```
