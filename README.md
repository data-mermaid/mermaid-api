# WCS MERMAID API

![Deployment](https://github.com/data-mermaid/mermaid-api/actions/workflows/deploy-cdk.yml/badge.svg)

## [API User Documentation](https://mermaid-api.readthedocs.io/)

## Stack

- [Django](https://www.djangoproject.com/) (Python)
- [Gunicorn](https://gunicorn.org/) (wsgi)
- [Nginx](https://www.nginx.com/) (webserver)
- [Supervisor](http://supervisord.org/) (process control)
- [Debian](https://www.debian.org/releases/stretch/) (OS)
- [Docker](https://www.docker.com/) (container)

## Local Development Workflow

Common workflow tasks are wrapped up using gnu's [make](https://makefiletutorial.com/) command. Refer to `Makefile` for the current commands. Add commands as required.

## Local Development Setup

### Installation

This project uses Docker for configuring the development environment and managing it. By overriding the container's 
environment variables, the same Docker image can be used for the production service. Thus, for development work, you
 must have Docker installed and running. 
 
Note that the following covers only local configuration, not deployment. See the 
[IAC README](iac/README.md) in this repository for more information.
 
### Environment variables

1. copy the sample `.secrets.env.sample` file and fill in the blanks: 
- `cp .secrets.env.sample .secrets.env`

2. copy the sample `.env.sample` file and fill in the blanks: 
- `cp .env.sample .env`

### Local environment initialization

#### Pre-commit

To maintain code quality, this project uses [pre-commit](https://pre-commit.com/) to run a series of checks on the code before it is committed. To install pre-commit, run the following:
`pip install pre-commit`

To use:
```sh
## Create a virtual environment
virtualenv venv
source venv/bin/activate  #Mac
source venv/Scripts/activate #Windows

## Install packages
pip install -r requirements-dev.txt
pre-commit install
```

When updating the local development python environment, be sure to run `pre-commit uninstall` followed by `pre-commit install`.

Once Docker is installed and local environment variables set, run the following:

```sh
$ make build
$ make up
```

If this is the first time running the up command, the api image will be built and postgis image will be downloaded. 
Then the containers will be started. 

With a database already created and persisted in an S3 bucket via 
```sh
$ make dbbackup
``` 

```sh
$ make dbrestore
``` 
will recreate and populate the local database with the latest dump. Without the S3 dump (i.e. running for the first time), you'll need to create a local database and then run 

 ```sh
$ make migrate
``` 
to create its schema.

A shortcut for the above steps, once S3 is set up, is available via:

```sh
$ make freshinstall:[env]

env: local (default), dev, prod
```

### Running the Webserver

Once everything is installed, run the following to have the API server running in the background:

```sh
$ make runserver
```

### Further

The project directory `api` is mounted to the container, so any changes you make outside the container (e.g. using 
an IDE installed on your host OS) are available inside the container.

Please note that running `make up` does NOT rebuild the image. So if you are making changes to the Dockerfile, for 
example adding a dependency to the `requirement.txt` file, you will need to do the following:

```
$ make down  // Stops and Removes the containers
$ make build  // Builds a new image
$ make up
```

> Note: this will delete your local database; all data will be lost.

### Database commands

```
$ make dbbackup:<env>

env: local, dev, prod
```

Backup the database from a named S3 key

```
$ make dbrestore:<env>

env: local, dev, prod
```

## Related repos

The MERMAID API forms the backbone for a growing family of apps that allow for coral reef data collection, 
management and reporting, and visualization:
https://github.com/data-mermaid

## Contributing

Pull Requests welcome! When we move to Python 3 this repo will use [Black](https://black.readthedocs.io/en/stable/). Send development questions to 
admin@datamermaid.org.


## Other Topics

### Collect Record

* [Push/Pull](src/api/resources/sync/README.md)
* [Validations v2](src/api/submission/validations2/README.md)

### SSH into containers in the cloud

- Install [Session Manager Plugin for AWS-CLI](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) locally
- Ensure AWS `mermaid` profile is set (~/.aws/config and ~/.aws/credentials)
- Ensure AWS resource IDs are set in environment
  - export MERMAID_CLUSTER=
  - export MERMAID_SERVICE=
  - export MERMAID_DBHOST=
  - export MERMAID_DBPORT=
- `$ make cloud_shell`
- su webapp
- bash

