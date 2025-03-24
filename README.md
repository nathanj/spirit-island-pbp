# Spirit Island PBP Helper

A website to assist playing Spirit Island over discord in the play by post section.

## Pre-requisites

Ensure that you've installed [Python](https://www.python.org/downloads/) and [Poetry](https://python-poetry.org/docs/#installing-with-pipx) before starting.

## Running locally

Copy `.env.template` to `.env` and fill in the variables

```
poetry install --no-root
poetry run ./manage.py migrate auth
poetry run ./manage.py migrate
poetry run ./manage.py collectstatic
poetry run ./manage.py runserver
```

*NOTE*: If running in a Windows shell, instead run the above manage.py commands with the format `poetry run python .\manage.py [...]`. E.g.

```
poetry run python .\manage.py migrate auth
```

## Test

```
poetry run ./manage.py test
```

## Making a new admin account for your instance

```
poetry run ./manage.py createsuperuser
```

## Troubleshooting

If you encounter file not found errors on Windows when running `poetry install` with paths that look similar to the following:

```
C:\Users\username\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\Local\pypoetry\Cache\virtualenvs\spirit-island-zmMjpaKz-py3.12\Lib\site-packages\pkg_resources\tests\data\my-test-package_unpacked-egg\my_test_package-1.0-py3.7.egg\EGG-INFO
```

The problem is likely that the path exceeds Windows' default allowed path length.
You can fix this by launching `regedit`, navigating to `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`, and editing the `LongPathsEnabled` key from 0 to 1.

## Docker Compose
By default the Docker compose deployment publishes the same port the app uses (8000) on your host, so you will likely not need to modify any reverse proxy or network configuration.

The default [docker/docker-compose.yaml file](./docker-compose.yaml) binds the app directory so live edits to files on the Docker host should propogate automaticaly to containers. The Redis container also binds the `cache` directory to make data backups available on the Docker host.

### Setup
Most of your environment variables can stay the same, but several are overridden in the docker-compose.yaml file to facilitate running the app in a Docker environment:
- `ALLOWED_IPS`: Set to the default Docker network ranges.
- `DJANGO_HOST`: Set to communicate with the Django API container in the deployment.
- `REDIS_HOST`: Set to communicate with the Redis container in the deployment.

### Use
```bash
# (Re)build the image
docker compose build
# Start the API/bot/Redis
docker compose up -d
# View containter states
docker compose ps
# To follow logs
docker compose logs -f
```

You can use the `app` [alias](./Dockerfile#L32) to run commands directly against the API Django app in the `sipbp` container. You can also use `/bin/bash` if you want to open a shell:
```bash
# View the help commands
docker compose exec -it sipbp app help
# Run a test request between the bot and the API
docker compose exec sibot /bin/bash -c 'apt install curl -y && curl sipbp:8000/api/ip'
# Create a new superuser
docker compose exec -it sipbp app createsuperuser
# Open a shell session for live debug/edits in the API container
docker compose exec -it sipbp /bin/bash
# Open a shell session for live debug/edits in the Discord bot container
docker compose exec -it sibot /bin/bash
```

You can also restart individual components by restarting their respective containers
```bash
# Restart the app
docker compose down sipbp && docker compose up sipbp
# Restart the bot
docker compose down sibot && docker compose up sibot
# Restart Redis
docker compose down siredis && docker compose up siredis
```

Or you can tear down the whole setup and rebuild it all with the same configs from scratch:
```bash
# Stop the whole setup
docker compose down
# (Re)build and restart the whole setup
docker compose up --build -d
docker compose logs -f
```