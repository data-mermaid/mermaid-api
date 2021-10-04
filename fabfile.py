import time

from invoke import run, task

# HELPER FUNCTIONS ###


def _api_cmd(cmd):
    """Prefix the container command with the docker cmd"""
    return "docker exec -it api_service %s" % cmd


def local(command):
    run(command, pty=True)


# FABRIC COMMANDS ###

def create_version_file():
    local("./ci_cd/version.sh")

@task
def build(c):
    """Run to build a new image prior to fab up"""
    create_version_file()
    local("docker-compose build")


@task(aliases=["build-nocache"])
def buildnocache(c):
    """Run to build a new image prior fab up"""
    create_version_file()
    local("docker-compose build --no-cache --pull")


@task
def up(c):
    """Create and start the mermaid-api services
    Note: api_db takes a minute or more to init.
    """
    local("docker-compose up -d")


@task
def down(c):
    """Stop and remove the mermaid-api services"""
    local("docker-compose down")


@task
def runserver(c):
    """Enter Django's runserver on 0.0.0.0:8080"""
    local(_api_cmd("python manage.py runserver 0.0.0.0:8080"))


@task
def runserverplus(c):
    """Enter gunicorn runserver on 0.0.0.0:8080"""
    local(_api_cmd("gunicorn --reload -c runserverplus.conf app.wsgi:application"))


@task
def makemigrations(c):
    """Run Django's makemigrations"""
    local(_api_cmd("python manage.py makemigrations"))


@task
def migrate(c):
    """Run Django's migrate"""
    local(_api_cmd("python manage.py migrate"))


@task
def shell(c):
    """ssh into the running container"""
    local("docker exec -it api_service /bin/bash")


@task
def dbshell(c):
    local(_api_cmd("python manage.py dbshell"))


@task
def shellplus(c):
    """Run Django extensions's shell_plus"""
    local(_api_cmd("python manage.py shell_plus"))


@task
def lint(c):
    """Run pylint"""
    local(_api_cmd("pylint --load-plugins pylint_django api"))


@task
def test(c):
    """Run unit tests"""
    local("docker exec -it api_service pytest --nomigrations --cov-report=html --cov=api --verbose api/tests")


@task 
def dbrestore(c, keyname="local"):
    """Restore the database from a named s3 key
        ie - fab dbrestore --keyname dev
    """
    local(_api_cmd("python manage.py dbrestore {}".format(keyname)))


@task
def dbbackup(c, keyname="local"):
    """Backup the database from a named s3 key
        ie - fab dbbackup --keyname dev
    """
    local(_api_cmd("python manage.py dbbackup {}".format(keyname)))


@task
def freshinstall(c, keyname="local"):
    down(c)
    buildnocache(c)
    up(c)

    time.sleep(20)
    dbrestore(c, keyname)
    migrate(c)
