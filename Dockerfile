# Base image versions. DEBIAN_CODENAME also selects the PGDG apt repo, so it
# must match the base image's Debian release.
ARG PYTHON_VERSION=3.13
ARG DEBIAN_CODENAME=bookworm

# App user and paths, shared by all stages. ENV PATH/PYTHONPATH and APP_DIR are
# derived from these, so a different APP_USER produces a consistent image.
ARG APP_USER=webapp
ARG APP_UID=1000

# ============================================================
# Stage 1: Builder — install build deps and compile pip pkgs
# ============================================================
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_CODENAME} AS builder
ARG APP_USER
ARG APP_UID

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd ${APP_USER} && useradd -m --no-log-init --uid ${APP_UID} -g ${APP_USER} ${APP_USER}

WORKDIR /var/projects/${APP_USER}
COPY requirements.txt .
# Install, then drop the packages' own test suites in the same layer. Nothing
# imports them at runtime; the runtime-stage checks below confirm the app still
# imports. Bytecode is kept so containers do not recompile on every start.
RUN su -l ${APP_USER} -c "pip install --no-cache-dir -r /var/projects/${APP_USER}/requirements.txt" \
 && find /home/${APP_USER}/.local -type d -name tests -prune -exec rm -rf {} +

# ============================================================
# Stage 2: Runtime — lean production image
# ============================================================
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_CODENAME} AS runtime
ARG DEBIAN_CODENAME
ARG APP_USER
ARG APP_UID
ARG APP_DIR=/var/projects/${APP_USER}
LABEL maintainer="<sysadmin@datamermaid.org>"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONPATH="${APP_DIR}"
ENV PATH="/home/${APP_USER}/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=app.settings

# Install runtime-only OS deps (no build-essential, libpq-dev, python3-dev).
# Django GIS only loads the GDAL shared library. gdal-bin is not used (the app
# runs no GDAL CLI tools) and hard-depends on Debian's python3, python3-gdal and
# python3-numpy. libgdal39 is the GDAL 3.13 library from PGDG; the build fails
# loudly if a GDAL upgrade renames it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
 && wget --quiet -O /usr/share/keyrings/pgdg.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
 && gpg --homedir "$(mktemp -d)" --dry-run --import --import-options show-only --with-colons /usr/share/keyrings/pgdg.asc \
      | awk -F: '/^fpr:/ {print $10}' \
      | grep -qx 'B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8' \
 && echo "deb [signed-by=/usr/share/keyrings/pgdg.asc] https://apt.postgresql.org/pub/repos/apt ${DEBIAN_CODENAME}-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    postgresql-client-16 \
    libgdal39 \
 && apt-get purge -y --auto-remove gnupg \
 && rm -rf /var/lib/apt/lists/*

# gunicorn will listen on this port
EXPOSE 8081

# Create the app dir owned by the app user. WORKDIR alone would create it as
# root, and COPY --chown does not change an existing destination directory.
RUN groupadd ${APP_USER} && useradd -m --no-log-init --uid ${APP_UID} -g ${APP_USER} ${APP_USER} \
 && install -d -o ${APP_USER} -g ${APP_USER} ${APP_DIR}

# Copy only the installed Python packages from the builder stage
COPY --from=builder --chown=${APP_USER}:${APP_USER} /home/${APP_USER}/.local /home/${APP_USER}/.local

WORKDIR ${APP_DIR}

COPY --chown=${APP_USER}:${APP_USER} ./src .
COPY --chown=${APP_USER}:${APP_USER} ./iac/settings ./iac/settings

# Run everything from here forward as non-root
USER ${APP_USER}:${APP_USER}

# Smoke test in the runtime stage, against runtime libraries only: psycopg loads
# libpq, and collectstatic sets up Django with every installed app. (`manage.py
# check` cannot run here: importing the URL conf queries the database.)
RUN python -c "import psycopg, pandas, pyarrow" \
 && SECRET_KEY='abc' python manage.py collectstatic --noinput

# Container health check for the API web server. Probes the DB-independent
# liveness path served by HealthEndpointMiddleware (returns before auth/DB), via
# the already-installed wget. start-period covers migrations + gunicorn boot.
#
# On ECS (EC2 launch type) Docker still runs this check inside the container,
# but ECS does not act on the result (no task-definition healthCheck is set).
# The scheduled tasks (ScheduledBackupTask, SummaryCacheTask) override CMD with a
# management command and run to completion, so their health signal is the
# container exit code, not an HTTP probe.
#
# Exec form (no shell): wget is the health-check process itself. With the shell
# form, Docker's timeout killed only the `sh`, and the orphaned wget was
# reparented to PID 1. When gunicorn was PID 1, wget's exit code 4 (network
# failure) made gunicorn halt with "App failed to load."
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD ["wget", "--quiet", "--tries=1", "--timeout=3", "--spider", "http://localhost:8081/health/"]

# Relative to WORKDIR (APP_DIR), so it follows APP_USER.
CMD ["./docker-entry.sh"]

# ============================================================
# Stage 3: Dev — adds test/dev dependencies on top of runtime
# ============================================================
FROM runtime AS dev
ARG APP_USER

USER root
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN su -l ${APP_USER} -c "pip install --no-cache-dir -r /tmp/requirements-dev.txt" \
 && rm /tmp/requirements-dev.txt
USER ${APP_USER}:${APP_USER}
