"""

Project Command File. Add any helper type commands here for automating
local workflow tasks.

For adding commands and using other Fabric.API comamnds,
    see: http://docs.fabfile.org/en/1.12/tutorial.html

Example of calling the up command:
    $ fab up

"""
import os
import time
from fabric.api import local

### HELPER FUNCTIONS ###


def _api_cmd(cmd):
    """Prefix the container command with the docker cmd"""
    return "docker exec -it api_service %s" % cmd

### FABRIC COMMANDS ###


def build():
    """Run to build a new image prior fab up"""

    local("docker-compose build")


def build_nocache():
    """Run to build a new image prior fab up"""

    local("docker-compose build --no-cache")


def up():
    """Create and start the mermaid-api services
    Note: api_db takes a minute or more to init.
    """
    local("docker-compose up -d")


def winup():
    """Version of up() for use in Windows Docker Toolbox env
    Requires: https://github.com/vweevers/node-docker-share
    See: https://github.com/docker/compose/issues/2548
    """
    import os

    path = os.path.dirname(os.path.realpath(__file__))
    local("docker-share mount -t %s/src" % path)
    up()


def down():
    """Stop and remove the mermaid-api services"""
    local("docker-compose down")


def runserver():
    """Enter Django's runserver on 0.0.0.0:8080"""
    local(_api_cmd("python manage.py runserver 0.0.0.0:8080"))


def collectstatic():
    """Run Django's collectstatic"""
    local(_api_cmd("python manage.py collectstatic"))


def makemigrations():
    """Run Django's makemigrations"""
    local(_api_cmd("python manage.py makemigrations"))


def migrate():
    """Run Django's migrate"""
    local(_api_cmd("python manage.py migrate"))


def shell_plus():
    """Run Django extensions's shell_plus"""
    local(_api_cmd("python manage.py shell_plus"))


def lint():
    """Run unit test"""
    local(_api_cmd("pylint --load-plugins pylint_django api"))


def shell():
    """ssh into the running container"""
    local("docker exec -it api_service /bin/bash")


def shell_db():
    """ssh into the running container"""
    local("docker exec -it api_db /bin/bash")


def test():
    """ssh into the running container"""
    local("docker exec -it api_service pytest --cov-report=html --cov=api --verbose")


def init_db():
    """Init the database after the services are up"""
    create_db()
    db_restore()


def refresh_base():
    """Insert lookups and basic entities as part of setting up dev environment fresh.
    NOTE: THIS WILL WIPE OUT EXISTING DATA FIRST."""
    local(_api_cmd("python manage.py refresh_base"))


def refresh_benthic():
    """Insert or update benthic attribute data from csv.
    Does NOT overwrite existing data."""
    local(_api_cmd("python manage.py refresh_benthic"))


def refresh_fish():
    """Insert or update fish attribute data from csv.
    Does NOT overwrite existing data."""
    local(_api_cmd("python manage.py refresh_fish"))


def refresh_model_choices():
    """Insert or update fish attribute data from csv.
    Does NOT overwrite existing data."""
    local(_api_cmd("python manage.py refresh_model_choices"))


def db_restore(key_name):
    """Restore the database from a named s3 key
        ie - fab db_restore:dev
    """
    local(_api_cmd("python manage.py dbrestore {}".format(key_name)))


def db_backup(key_name):
    """Backup the database from a named s3 key
        ie - fab db_backup:dev
    """
    local(_api_cmd("python manage.py dbbackup {}".format(key_name)))


def create_db():
    raise NotImplementedError()
    create_sql = """
        CREATE DATABASE mermaid
                WITH
                OWNER = postgres
                ENCODING = 'UTF8'
                CONNECTION LIMIT = -1;
    """


def fresh_install(key_name=None):
    key_name = key_name or 'local'

    down()
    build()
    if os.name == 'nt':
        winup()
    else:
        up()

    time.sleep(20)
    db_restore(key_name)
    migrate()
