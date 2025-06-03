# docker build -t sipbp:latest .
FROM ubuntu:latest

WORKDIR /app
ENV DEBIAN_FRONTEND="noninteractive"
ENV TZ="Etc/UTC"
ENV POETRY_VERSION="1.8.2"
ENV PYTHONUNBUFFERED="TRUE"

COPY . .
EXPOSE 8000

# python
RUN apt update && apt install -y \
  curl \
  git \
  python3 \
  python3-pip \
  libjpeg-dev

# poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# install app
RUN poetry --version && \
  poetry install --no-root && \
  poetry run python3 /app/manage.py collectstatic --noinput && \
  poetry run python3 /app/manage.py migrate

# add aliases for ease of use
RUN echo '#!/bin/bash\npoetry run python3 /app/manage.py "$@"' > /usr/bin/app && \
  chmod +x /usr/bin/app
RUN echo '#!/bin/bash\npoetry run python3 /app/bot.py "$@"' > /usr/bin/bot && \
  chmod +x /usr/bin/bot

# add app dir to path
ENV PATH="/app:$PATH"

# test the app and its alias
RUN app test

HEALTHCHECK CMD curl --fail http://localhost:8000 || echo 1
ENTRYPOINT ["entrypoint.sh"]
