FROM python:3.10-slim-bullseye
LABEL maintainer="<sysadmin@datamermaid.org>"

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8
ENV DJANGO_SETTINGS_MODULE="app.settings"
ENV PYTHONPATH="/var/projects/webapp"
ENV PATH="/home/webapp/.local/bin:${PATH}"

WORKDIR /var/projects/webapp

RUN groupadd webapps
RUN useradd -m webapp -G webapps
# RUN mkdir -p /var/log/webapp/ && chown -R webapp /var/log/webapp/ && chmod -R u+rX /var/log/webapp/
# RUN mkdir -p /var/run/webapp/ && chown -R webapp /var/run/webapp/ && chmod -R u+rX /var/run/webapp/
# RUN mkdir -p /etc/gunicorn/
# ADD ./gunicorn_webapp.py /etc/gunicorn/webapp.py

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends \
    gnupg \
    build-essential \
    libpq-dev \
    python3-dev \
    wget \
    vim \
    nano \
    gunicorn \
    postgresql-client-13 \
    gdal-bin \
    python3-gdal

ADD . /var/projects/webapp
RUN chown -R webapp:webapp .
RUN rm -rf /var/projects/webapp/static

USER webapp
RUN pip install --user --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080 80
CMD ["/bin/bash", "/var/projects/webapp/entry.sh" ]