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

### Setup
Create a `.env` file from the [.env.template file](./.env.template) and change out the values as needed.
```bash
cp .env.template .env
```

Most of the values can be left as is, but the following need to be updated in most cases:
- `GAME_URL`: Set this to your API's domain or `".*"` to bypass the host valdiation for incoming traffic. If using `".*"`, you should setup the `CUSTOM_API_KEY` shared secret to validate traffic is coming from the bot and not somewhere else.
- `DISCORD_KEY`: Discord bot token. See https://www.writebots.com/discord-bot-token.
- `EXTRA_ALLOWED_HOSTS`: Domain where you plan on hosting. You'll see `CSRF` errors if this is set incorrectly.
- `DJANGO_SUPERUSER_EMAIL`: Email you want to use for default admin user.
- `DJANGO_SECRET_KEY`: Secret key for Django server. Removing this will use a default dev key.
- `DISCORD_GUILD_ID`: ID of the Discord Guild (Discord server) to connect to.
- `CUSTOM_API_KEY`: Put some random string of characters here. Can generate one here: https://1password.com/password-generator.

### Use
```bash
# (Re)build the image
docker compose build
# Start the API/bot/DB
docker compose up -d
# To follow logs
docker compose logs -f
```

You can use the `app` [alias](./Dockerfile#L32) to run commands directly against the API in the `sipbp` container. You can also use `/bin/bash` if you want to open a shell:
```bash
# View the help commands
docker compose exec -it sipbp app help
# Create a new superuser
docker compose exec -it sipbp app createsuperuser
# Open a shell session for live debug/edits
docker compose exec -it sipbp /bin/bash
```

You can also restart individual components by restarting their respective containers
```bash
# Restart the app
docker compose down sipbp && docker compose up sipbp
# Restart the bot
docker compose down bot && docker compose up bot
# Restart Redis
docker compose down redis && docker compose up redis
```

Or you can tear down the whole setup and rebuild it all with the same configs from scratch:
```bash
# Stop the whole setup
docker compose down
# (Re)build and restart the whole setup
docker compose up --build -d
docker compose logs -f
```