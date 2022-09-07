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
RUN mkdir -p /var/log/webapp/ && chown -R webapp /var/log/webapp/ && chmod -R u+rX /var/log/webapp/
RUN mkdir -p /var/run/webapp/ && chown -R webapp /var/run/webapp/ && chmod -R u+rX /var/run/webapp/

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends \
    gnupg \
    build-essential \
    libpq-dev \
    python3-dev \
    wget \
    vim \
    nano \
    supervisor \
    nginx \
    gunicorn \
    postgresql-client-13 \
    gdal-bin \
    python3-gdal

ADD ./config/gunicorn.conf /
RUN rm /etc/nginx/sites-enabled/default && rm /etc/nginx/sites-available/default
ADD ./config/webapp.nginxconf /etc/nginx/sites-enabled/
RUN mkdir -p /var/log/supervisor
ADD ./config/supervisor_conf.d/*.conf /etc/supervisor/conf.d/

ADD ./requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --upgrade -r requirements.txt
RUN rm requirements.txt

ADD ./src .
ADD ./ci_cd/VERSION.txt .

EXPOSE 8000 80 443
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
