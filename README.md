# WCS MERMAID API

Master [![CircleCI](https://circleci.com/gh/data-mermaid/mermaid-api/tree/master.svg?style=svg)](https://circleci.com/gh/data-mermaid/mermaid-api/tree/master)

Dev [![CircleCI](https://circleci.com/gh/data-mermaid/mermaid-api/tree/dev.svg?style=svg)](https://circleci.com/gh/data-mermaid/mermaid-api/tree/dev)

[API User Documentation](https://mermaid-api.readthedocs.io/)

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
 
### Environment variables

1. copy the sample `.secrets.env.sample` file and fill in the blanks: 
- `cp .secrets.env.sample .secrets.env`

2. copy the sample `.env.sample` file and fill in the blanks: 
- `cp .env.sample .env`

### Local environment intialization

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
$ fab freshinstall:[env]

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


## Other Topics

### Collect Record

* [Push/Pull](src/api/resources/sync/README.md)
* [Validations v2](src/api/submission/validations2/README.md)

### SSH into containers in the cloud

Requirements: 
- Install [Session Manager Plugin for AWS-CLI](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) locally

Then, log into the AWS console and identify the task ID of the ECS container that you want to "exec" into. Once you have the task ID, replace the XXX in the command below:

```
$ make cloud_shell taskid=XXX
```