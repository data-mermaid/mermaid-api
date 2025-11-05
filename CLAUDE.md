# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

MERMAID API is a Django-based REST API for coral reef data collection, management, and reporting. The API serves as the backbone for the MERMAID family of applications that enable coral reef monitoring and analysis.

**Stack:** Django, Django REST Framework, PostGIS, Docker, Gunicorn, Nginx

**API Documentation:** https://mermaid-api.readthedocs.io/

## Development Commands

All development happens in Docker containers. The project uses `make` commands for all development workflows.

**Note:** `fabfile.py` is deprecated. Use `Makefile` commands instead.

### Docker & Environment Setup

**Initial setup:**
```bash
# Copy environment files
cp .secrets.env.sample .secrets.env
cp .env.sample .env
# Fill in the environment variables in both files

# Fresh install (recommended for first-time setup)
make freshinstall
# This will: down containers -> build image -> start containers -> restore DB from S3 -> run migrations
```

**Build & Run:**
```bash
make build           # Build Docker image
make buildnocache    # Build without cache (needed when Dockerfile or requirements.txt changes)
make up              # Start containers (alias: make start)
make down            # Stop and remove containers (alias: make stop)
make downnocache     # Stop containers and remove volumes (deletes local DB!)
make logs            # Follow logs from api_service container
```

**Running the server:**
```bash
make runserver       # Start Django dev server on http://localhost:8080
make runserverplus   # Start Gunicorn server (production-like on port 8081)
```

### Database Commands

```bash
make migrate         # Apply migrations
make dbbackup        # Backup local DB to S3 (uses 'local' keyname)
make dbrestore       # Restore local DB from S3 (uses 'local' keyname)
```

**Django database shells:**
```bash
make shellplus       # Django shell with models auto-imported
# Or run manually: docker exec -it api_service python manage.py dbshell
# Or for makemigrations: docker exec -it api_service python manage.py makemigrations
```

**Note:** Running `make down` followed by `make build` followed by `make up` will delete your local database. Use `make dbrestore` to restore from S3.

### Testing & Code Quality

```bash
# Run all tests
make test
# Runs: pytest -v --no-migrations --rich api/tests

# Run a single test
docker exec -it api_service pytest --no-migrations api/tests/path/to/test_file.py::TestClass::test_method

# Linting and formatting (run outside Docker via pre-commit)
# Pre-commit runs: isort (import sorting), ruff (linting), ruff-format (code formatting)
virtualenv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install              # Install git pre-commit hooks
pre-commit run --all-files      # Run all checks manually on all files
```

### Other Useful Commands

```bash
make shell              # Bash shell in api_service container
make shellroot          # Bash shell as root user
make shellplus          # Django shell with models auto-imported
make shellplusroot      # Django shell as root user

# Background workers
make worker             # Run SQS worker (alias: make simpleq)

# AWS ECS cloud access (requires AWS credentials)
make cloudshell         # SSH into ECS container
make cloudtunnel        # Create SSH tunnel to RDS database
```

## Architecture

### Project Structure

```
src/
├── api/                      # Main Django app
│   ├── models/              # Django models
│   │   ├── mermaid.py       # Core domain models (Site, Project, etc.)
│   │   ├── sql_models/      # Protocol-specific SQL models (for data summaries)
│   │   └── view_models/     # Database views
│   ├── resources/           # API ViewSets and Serializers
│   │   ├── sampleunitmethods/  # Protocol-specific endpoints
│   │   └── sync/            # Push/Pull sync endpoints (see README)
│   ├── submission/          # Data validation and submission logic
│   │   ├── validations/     # Validation rules per protocol
│   │   ├── parser.py        # Parse incoming submissions
│   │   └── writer.py        # Write validated data to DB
│   ├── reports/             # Report generation
│   ├── ingest/              # CSV data ingestion
│   ├── middleware.py        # Custom middleware (metrics, API version)
│   └── auth_backends.py     # Auth0 JWT authentication
├── app/                     # Django project settings
│   ├── settings.py          # Main settings file
│   └── urls.py              # URL routing
├── simpleq/                 # SQS-based task queue (modified SimpleQ)
├── sqltables/               # SQL table management
└── tools/                   # Management commands and utilities
```

### Key Architectural Concepts

**1. Protocol-Based Data Collection**

MERMAID supports multiple survey protocols (Belt Fish, Benthic LIT, Benthic PIT, Benthic PQT, Bleaching QC, Habitat Complexity). Each protocol has:
- A sample unit method model (defines the survey method)
- Observation models (actual survey data)
- SQL models for data summaries (Observation, Sample Unit, Sample Event levels)
- API endpoints for Obs/SU/SE data at three summary levels
- Validation rules in `src/api/submission/validations/`

**2. Three-Tier Data Summary System**

Each protocol exposes data at three levels:
- **Observation (Obs):** Raw observation-level data
- **Sample Unit (SU):** Aggregated per transect/quadrat
- **Sample Event (SE):** Aggregated per site visit

Each level has CSV, JSON, and GeoJSON serializers.

**3. Sync Architecture (Push/Pull)**

The API supports offline-first mobile apps via a revision-based sync system:
- **Pull:** Clients fetch updates/deletes since last revision number
- **Push:** Clients submit new/modified/deleted records
- System properties: `_last_revision_num`, `_modified`, `_deleted`
- See: `src/api/resources/sync/README.md`

**4. Data Submission & Validation**

Submission flow:
1. Client POSTs data to collect record endpoint
2. `parser.py` parses and structures the data
3. Protocol-specific validators run (in `submission/validations/`)
4. `writer.py` persists validated data
5. SQL summary models are updated via database triggers/signals

**5. Task Queue (SimpleQ)**

Uses AWS SQS for asynchronous processing:
- Image classification tasks
- Report generation
- Data exports
- Worker started via: `python manage.py simpleq_worker`

**6. Authentication**

Uses Auth0 JWT tokens via custom `JWTAuthentication` backend in `api/auth_backends.py`.

### Database

- **Engine:** PostGIS (PostgreSQL with spatial extensions)
- **Migrations:** Standard Django migrations
- **Test DB:** Uses separate `test_mermaid` database
- **Views:** Some models are database views (see `view_models/`)

### Adding a New Protocol

See `new_protocol_readme.md` for a comprehensive checklist covering:
- Models (sample unit, observations, SQL models)
- Admin configuration
- CSV ingest schema
- Validation rules
- API endpoints (Obs/SU/SE viewsets)
- URL routing

## Important Files

- `Makefile` - Development workflow commands (build, test, run, etc.)
- `fabfile.py` - **DEPRECATED** (use Makefile instead)
- `src/app/settings.py` - Django settings (environment-based configuration)
- `src/api/urls.py` - API URL routing
- `src/pytest.ini` - Pytest configuration
- `.pre-commit-config.yaml` - Pre-commit hooks configuration (isort, ruff, ruff-format)
- `pyproject.toml` - Tool configurations for isort, ruff
- `.isort.cfg` - Import sorting configuration

## Testing

- Tests are in `src/api/tests/`
- Use pytest with Django plugin
- Run with `--no-migrations` flag for speed
- Uses `--rich` flag for better output formatting
- Test command runs inside Docker container via `make test`

## Environment Variables

Required variables are in `.secrets.env` and `.env`:
- **Auth0:** `AUTH0_DOMAIN`, `MERMAID_API_AUDIENCE`, `MERMAID_API_SIGNING_SECRET`
- **AWS:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, S3 bucket names
- **Database:** `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- **Email:** `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- **SQS:** `SQS_QUEUE_NAME`, `IMAGE_SQS_QUEUE_NAME`

## API Versioning

API version is tracked via:
- `src/VERSION.txt` (auto-generated from git SHA during build)
- Exposed via `APIVersionMiddleware` in `HTTP_API_VERSION` header

## Maintenance Mode

Set `MAINTENANCE_MODE=True` to prevent DB writes and return 503 responses. Configurable to allow admin/staff/superuser access.
