# Spirit Island PBP Helper

A website to assist playing Spirit Island over discord in the play by post section.

## Running locally

Copy `.env.template` to `.env` and fill in the variables

```
poetry install --no-root
poetry run ./manage.py migrate auth
poetry run ./manage.py migrate pbf 0001
poetry run ./manage.py seeddb
poetry run ./manage.py migrate
poetry run ./manage.py collectstatic
poetry run ./manage.py runserver
```

## Test

```
poetry run ./manage.py test
```

## Making a new admin account for your instance

```
poetry run ./manage.py createsuperuser
```