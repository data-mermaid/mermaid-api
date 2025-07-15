FROM python:3.12-slim-bookworm
LABEL maintainer="<sysadmin@datamermaid.org>"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONPATH="/var/projects/webapp"
ENV PATH="/home/webapp/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=app.settings

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg lsb-release ca-certificates \
 && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
 && apt-get update \
 && apt-get install -y --no-install-recommends  \
    git \
    gnupg \
    build-essential \
    libpq-dev \
    python3-dev \
    postgresql-client-16 \
    gdal-bin \
    python3-gdal \
 && apt-get purge -y --auto-remove gnupg lsb-release \
 && rm -rf /var/lib/apt/lists/*

# gunicorn will listen on this port
EXPOSE 8081

ARG APP_USER=webapp
ARG APP_DIR=/var/projects/${APP_USER}
RUN groupadd ${APP_USER} && useradd -m --no-log-init -g ${APP_USER} ${APP_USER}

# Copy your application code to the container (make sure you create a .dockerignore file if any large files or directories should be excluded)
WORKDIR ${APP_DIR}

ADD requirements.txt .
RUN su ${APP_USER} -c "pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt"
RUN rm ${APP_DIR}/requirements.txt

ADD ./src .
ADD ./iac/settings ./iac/settings
RUN chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

# Run everything from here forward as non-root
USER ${APP_USER}:${APP_USER}

# Call collectstatic (customize the following line with the minimal environment variables needed for manage.py to run):
RUN SECRET_KEY='abc' python manage.py collectstatic --noinput

CMD ["/var/projects/webapp/docker-entry.sh"]
