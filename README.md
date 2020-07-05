# WCS MERMAID API

Master [![CircleCI](https://circleci.com/gh/data-mermaid/mermaid-api/tree/master.svg?style=svg)](https://circleci.com/gh/data-mermaid/mermaid-api/tree/master)

Dev [![CircleCI](https://circleci.com/gh/data-mermaid/mermaid-api/tree/dev.svg?style=svg)](https://circleci.com/gh/data-mermaid/mermaid-api/tree/dev)

## Stack

- [Django](https://www.djangoproject.com/) (Python)
- [Gunicorn](https://gunicorn.org/) (wsgi)
- [Nginx](https://www.nginx.com/) (webserver)
- [Supervisor](http://supervisord.org/) (process control)
- [Debian](https://www.debian.org/releases/stretch/) (OS)
- [Docker](https://www.docker.com/) (container)

## Local Development Workflow

Common workflow tasks are wrapped up using [Fabric](http://www.fabfile.org/) commands. Refer to `fabfile.py` for the 
current commands. Add commands as required.

## Local Development Setup

### Installation

This project uses Docker for configuring the development environment and managing it. By overriding the container's 
environment variables, the same Docker image can be used for the production service. Thus, for development work, you
 must have Docker installed and running. 
 
Note that the following covers only local configuration, not deployment. Nevertheless, see the directories outside of
 `src` for how we deploy to [Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/) using 
 [CircleCI](https://circleci.com/) and [Docker Hub](https://hub.docker.com/).
 
#### Environment variables

The following are the redacted key-val pairs for a local MERMAID `.env` file or for Elastic Beanstalk configuration 
settings:
```
AUTH0_MANAGEMENT_API_AUDIENCE=https://datamermaid.auth0.com/api/v2/
MERMAID_API_AUDIENCE=https://dev-api.datamermaid.org
MERMAID_API_SIGNING_SECRET=
SPA_ADMIN_CLIENT_ID=
SPA_ADMIN_CLIENT_SECRET=
MERMAID_MANAGEMENT_API_CLIENT_ID=
MERMAID_MANAGEMENT_API_CLIENT_SECRET=
DB_NAME=mermaid
DB_USER=postgres
PGPASSWORD=postgres
DB_PASSWORD=postgres
DB_HOST=api_db
DB_PORT=5432
RESTORE=local
BACKUP=local
AWS_BACKUP_BUCKET=mermaid-db-backups
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
ENV=local
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
ADMINS=
SUPERUSER=
MERMAID_DOMAIN=datamermaid.auth0.com
DEFAULT_DOMAIN_API=localhost:8080
DEFAULT_DOMAIN_COLLECT=localhost:8888
```

#### Local environment intialization

Once Docker is installed and local environment variables set, run the following:

```sh
$ fab build
$ fab up
```

If this is the first time running the up command, the api image will be built and postgis image will be downloaded. 
Then the containers will be started. 

With a database already created and persisted in an S3 bucket via 
```sh
$ fab dbbackup
``` 
,
```sh
$ fab dbrestore
``` 
will recreate and populate the local database with the latest dump. Without the S3 dump (i.e. running for the first time),
 you'll need to create a local database and then run 
 ```sh
$ fab migrate
``` 
to create its schema.

A shortcut for the above steps, once S3 is set up, is available via:

```
$ fab fresh-install:[env]

env: local (default), dev, prod
```

### Running the Webserver

Once everything is installed, run the following to have the API server running in the background:

```sh
$ fab runserver
```

### Further

The project directory `api` is mounted to the container, so any changes you make outside the container (e.g. using 
an IDE installed on your host OS) are available inside the container.

Please note that running `fab up` does NOT rebuild the image. So if you are making changes to the Dockerfile, for 
example adding a dependency to the `requirement.txt` file, you will need to do the following:

```
$ fab down  // Stops and Removes the containers
$ fab build  // Builds a new image
$ fab up
```

> Note: this will delete your local database; all data will be lost.

### Database commands

```
$ fab dbbackup:<env>

env: local, dev, prod
```

Backup the database from a named S3 key

```
$ fab dbrestore:<env>

env: local, dev, prod
```

## Related repos

The MERMAID API forms the backbone for a growing family of apps that allow for coral reef data collection, 
management and reporting, and visualization:
https://github.com/data-mermaid

## Contributing

Pull Requests welcome! When we move to Python 3 this repo will use [Black](https://black.readthedocs.io/en/stable/). Send development questions to 
admin@datamermaid.org.
