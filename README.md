# Spirit Island PBP Helper

A website to assist playing Spirit Island over discord in the play by post section.

## Pre-requisites

Ensure that you've installed [Python](https://www.python.org/downloads/) and [Poetry](https://python-poetry.org/docs/#installing-with-pipx) before starting.

## Running the site locally

Copy `.env.template` to `.env` and fill in the variables

```
poetry install --no-root
poetry run ./manage.py migrate auth
poetry run ./manage.py migrate
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

If no images are showing up when running locally, consider setting [`DEBUG`](https://docs.djangoproject.com/en/stable/ref/settings/#debug) to True.
In this project, this is done by setting the `DEBUG` environment variable to `yes` (the value that `island/settings.py` is checking for), typically using the `.env` file.
Doing so makes Django serve [static files](https://docs.djangoproject.com/en/stable/howto/static-files/) such as images.

If no images are showing up when running in production, check that you've configured your chosen web server to serve the static files (exact configuration depends on the web server).

If you encounter file not found errors on Windows when running `poetry install` with paths that look similar to the following:

```
C:\Users\username\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\Local\pypoetry\Cache\virtualenvs\spirit-island-zmMjpaKz-py3.12\Lib\site-packages\pkg_resources\tests\data\my-test-package_unpacked-egg\my_test_package-1.0-py3.7.egg\EGG-INFO
```

The problem is likely that the path exceeds Windows' default allowed path length.
You can fix this by launching `regedit`, navigating to `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`, and editing the `LongPathsEnabled` key from 0 to 1.

## Running the Discord bot

The Discord bot is responsible for receiving updates from the website and posting them to each game's update channel on Discord.
When running the site locally for development, typically the bot is not needed.
You only need the bot when specifically testing bot-related functionality.

You will need a running instance of [Redis](https://redis.io/) for the Discord bot to receive updates from the website.

You can locally test whether the bot is correctly receiving updates with these steps:

1. Set the Discord channel for a test game to any non-empty value.
   You can use the Django admin interface to do this.
1. `poetry run python bot.py --fake-discord`
1. Make a change in the test game that will produce a log message.
1. Check the bot's output on stdout to see whether it receives the messages.
   The output will say "got message" when it receives it, and "sending" when it would send it to Discord.

If you need an actual Discord connection:

1. Create an application in the Discord Developer Portal.
1. Under Settings → Bot, create a bot for this application, and also do the following:
    * Enable the Message Content Intent, as the bot examines messages for commands like `$follow`.
    * Create a token for the bot.
      This token must be provided to `bot.py` as environment variable `DISCORD_KEY`.
      Recall that `.env` can be used to provide the environment variable.
1. Invite the bot to your server if you have the Manage Server permission, or ask someone who does to invite it.
    * check Settings → Installation for the format of the invite link if you need a reminder of what one should look like.
    * You can use the `--list-guilds` flag to `bot.py` to check whether the guild is visible to the bot.

The bot does not require any server-wide permissions, only permissions specific to channels where game updates will be posted.

* Required: View Channel
* Required: Send Messages
* Required: Attach Files
* Optional: Use External Emoji (If you want the bot to use Spirit Island emoji on a server other than Spirit Island)
* Optional: Add Reactions (If you want the bot to respond to commands via reactions instead of a separate message)
* Optional: Read Message History (Enables commands like `$pin`, where the bot needs to access the message that the command is replying to)
* Optional: Manage Messages (If you are comfortable allowing the bot to pin messages using the `$pin` command)
* Optional: Manage Channel (If you are comfortable allowing the bot to set the topic using the `$topic` command. **WARNING**: This permission also allows deleting the channel. While this bot will never do so, an attacker who acquires the bot's token will be able to use it to delete channels if given this permission.)

Once you have the bot added to the server,
the permissions set up for the bot on the game update channels,
and configured the bot's `DISCORD_KEY` and other settings,
you are ready to run the bot.

```
poetry run python bot.py
```

## Running the site in production

A full treatment of this topic is beyond the scope of this document, but here are some notes specific to this project:

* Remember to turn `DEBUG` off in the `.env` file.
* `poetry run ./manage.py collectstatic` will copy all [static files](https://docs.djangoproject.com/en/stable/howto/static-files/) into `static/`.
  You will need to configure your web server to serve static files out of this directory.
* You will also need to configure your web server to serve uploaded files out of the `screenshots/` directory.
* This repo already contains all the necessary configuration to be run by [Gunicorn](https://gunicorn.org/).
* [Gunicorn deployment docs](https://docs.gunicorn.org/en/latest/deploy.html) recommend deploying Gunicorn behind a proxy server.
  They themselves recommend [nginx](https://nginx.org/).
  [Caddy](https://caddyserver.com/) is also known to work well; see the Caddyfile provided in this repo for a usable config.
* If you'd prefer to use Docker, consider a [community-contributed Docker configuration](https://github.com/nathanj/spirit-island-pbp/pull/152).

Further advice can be found in the [Django deployment docs](https://docs.djangoproject.com/en/stable/howto/deployment/).
