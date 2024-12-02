FROM python:3.10-slim-bullseye as main
LABEL maintainer="<sysadmin@datamermaid.org>"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONPATH="/var/projects/webapp"
ENV PATH="/home/webapp/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

# Add any static environment variables needed by Django or your settings file here:
ENV DJANGO_SETTINGS_MODULE=app.settings

# Install OS dependencies
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends \
    git \
    gnupg \
    build-essential \
    libpq-dev \
    python3-dev \
    postgresql-client-13 \
    gdal-bin \
    python3-gdal

# gunicorn will listen on this port
EXPOSE 8081

ARG APP_USER=webapp
ARG APP_DIR=/var/projects/${APP_USER}
RUN groupadd ${APP_USER} && useradd -m --no-log-init -g ${APP_USER} ${APP_USER}

# Copy your application code to the container (make sure you create a .dockerignore file if any large files or directories should be excluded)
WORKDIR ${APP_DIR}

ADD requirements.txt .
RUN su ${APP_USER} -c "pip install --no-cache-dir -r requirements.txt"
RUN rm ${APP_DIR}/requirements.txt

ADD ./src .

RUN chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

# Run everything from here forward as non-root
USER ${APP_USER}:${APP_USER}

# Call collectstatic (customize the following line with the minimal environment variables needed for manage.py to run):
RUN SECRET_KEY='abc' python manage.py collectstatic --noinput

CMD ["/var/projects/webapp/docker-entry.sh"]


FROM main as lambda_function

ADD ./iac/settings ./iac/settings
ADD ./scripts/ ./scripts

# Install AWS lambda RIC
RUN pip install awslambdaric

ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "worker_function.run_cmd_w_env.lambda_handler" ]
