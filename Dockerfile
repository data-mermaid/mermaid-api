# ============================================================
# Stage 1: Builder — install build deps and compile pip pkgs
# ============================================================
FROM python:3.12-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

ARG APP_USER=webapp
RUN groupadd ${APP_USER} && useradd -m --no-log-init -g ${APP_USER} ${APP_USER}

WORKDIR /var/projects/${APP_USER}
ADD requirements.txt .
# Pre-install CPU-only PyTorch before requirements.txt so pyspacer
# (which depends on torch) picks up the lighter wheel (~280 MB vs ~2 GB).
# ECS tasks run on t3a instances with no GPU.
RUN su ${APP_USER} -c "\
    pip install --upgrade pip \
 && pip install --no-cache-dir --no-compile \
        torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --no-compile -r requirements.txt"

# Strip unnecessary files from installed packages to shrink the layer
RUN find /home/${APP_USER}/.local -type d -name '__pycache__' -exec rm -rf {} + \
 && find /home/${APP_USER}/.local -type d -name 'tests' \
        ! -path '*/django/contrib/admin/tests' \
        -exec rm -rf {} + \
 && find /home/${APP_USER}/.local -name '*.pyc' -delete \
 && find /home/${APP_USER}/.local -name '*.pyo' -delete

# ============================================================
# Stage 2: Runtime — lean production image
# ============================================================
FROM python:3.12-slim-bookworm AS runtime
LABEL maintainer="<sysadmin@datamermaid.org>"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONPATH="/var/projects/webapp"
ENV PATH="/home/webapp/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=app.settings

# Install runtime-only OS deps (no build-essential, libpq-dev, python3-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg lsb-release ca-certificates \
 && echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    postgresql-client-16 \
    gdal-bin \
    python3-gdal \
 && apt-get purge -y --auto-remove wget gnupg lsb-release \
 && rm -rf /var/lib/apt/lists/*

# gunicorn will listen on this port
EXPOSE 8081

ARG APP_USER=webapp
ARG APP_DIR=/var/projects/${APP_USER}
RUN groupadd ${APP_USER} && useradd -m --no-log-init -g ${APP_USER} ${APP_USER}

# Copy only the installed Python packages from the builder stage
COPY --from=builder --chown=${APP_USER}:${APP_USER} /home/${APP_USER}/.local /home/${APP_USER}/.local

WORKDIR ${APP_DIR}

ADD ./src .
ADD ./iac/settings ./iac/settings
RUN chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

# Run everything from here forward as non-root
USER ${APP_USER}:${APP_USER}

# Call collectstatic (customize the following line with the minimal environment variables needed for manage.py to run):
RUN SECRET_KEY='abc' python manage.py collectstatic --noinput

CMD ["/var/projects/webapp/docker-entry.sh"]

# ============================================================
# Stage 3: Dev — adds test/dev dependencies on top of runtime
# ============================================================
FROM runtime AS dev

ARG APP_USER=webapp
USER root
ADD requirements-dev.txt /tmp/requirements-dev.txt
RUN su ${APP_USER} -c "pip install --no-cache-dir -r /tmp/requirements-dev.txt" \
 && rm /tmp/requirements-dev.txt
USER ${APP_USER}:${APP_USER}
