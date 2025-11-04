# Makefile Readme
# ----------------
#
# down: shut down docker containers (database and api containers).
# buildnocache: build new docker image without using cache.
# up: start docker containers (database and api containers).
# dbbackup: create a backup of your local database and push to S3.  NOTE: Local backups are used by all devs during database restore.
# dbrestore: restore a backup from s3 to your local database.
# migrate: apply any database migrations to local database.
# freshinstall:  helper command that wraps server commands to setup API, database and data locally.
# runserver: Start api web server, runs on http://localhost:8080/
# shell: Starts bash terminal inside the API docker container.
# 
# 
# To get started run `make freshinstall`
# 



API_SERVICE="api_service"
DOCKER_COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)


down:
	$(DOCKER_COMPOSE) down

downnocache:
	$(DOCKER_COMPOSE) down -v

stop:
	@make down

buildnocache:
	$(eval short_sha=$(shell git rev-parse --short HEAD))
	@echo $(short_sha) > src/VERSION.txt
	@cat src/VERSION.txt
	$(DOCKER_COMPOSE) build --no-cache --pull

build:
	$(eval short_sha=$(shell git rev-parse --short HEAD))
	@echo $(short_sha) > src/VERSION.txt
	@cat src/VERSION.txt
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

start:
	@make up

logs:
	$(DOCKER_COMPOSE) logs -f $(API_SERVICE)

dbbackup:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python manage.py dbbackup local

dbrestore:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python manage.py dbrestore local

migrate:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python manage.py migrate

install:
	@echo "\n--- Shutting down existing stack ---\n"
	@make down
	@echo "\n--- Building new docker image ---\n"
	@make build
	@echo "\n--- Spinning up new stack ---\n"
	@make up
	@sleep 20
	@echo "\n--- Applying MERMAID database migrations ---\n"
	@make migrate

freshinstall:
	@echo "\n--- Shutting down existing stack ---\n"
	@make downnocache
	@echo "\n--- Building new docker image ---\n"
	@make buildnocache
	@echo "\n--- Spinning up new stack ---\n"
	@make up
	@sleep 20
	@echo "\n--- Restoring MERMAID database ---\n"
	@make dbrestore
	@echo "\n--- Applying MERMAID database migrations ---\n"
	@make migrate

runserver:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python manage.py runserver 0.0.0.0:8080

worker:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python manage.py simpleq_worker

runserverplus:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) gunicorn app.wsgi \
  		--bind 0.0.0.0:8081 \
		--timeout 120 \
		--workers 2 \
		--threads 4 \
		--worker-class gthread \
		--access-logfile "-" \
		--error-logfile "-" \
		--worker-tmp-dir /dev/shm

simpleq:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python manage.py simpleq_worker

shellplus:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python manage.py shell_plus

shell:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) /bin/bash

shellroot:
	$(DOCKER_COMPOSE) exec --user=root $(API_SERVICE) /bin/bash

shellplusroot:
	$(DOCKER_COMPOSE) exec --user=root $(API_SERVICE) python manage.py shell_plus

test:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) pytest -v --no-migrations api/tests

# -----------------
# Fargate Maintenance (docker exec)
# -----------------
# Assume local profile name in ~/.aws/config is `mermaid`

cloudshell:
	$(eval taskid=$(shell aws ecs list-tasks --region us-east-1 --profile mermaid --cluster $(MERMAID_CLUSTER) --service-name $(MERMAID_SERVICE) --output text | awk -F'/' '{print $$3}'))
	echo $(taskid)
	aws ecs execute-command  \
		--profile mermaid \
		--region us-east-1 \
		--cluster $(MERMAID_CLUSTER) \
		--task $(taskid) \
		--container MermaidAPI \
		--command "/bin/bash" \
		--interactive

cloudtunnel:
	$(eval taskid=$(shell aws ecs list-tasks --profile mermaid --cluster $(MERMAID_CLUSTER) --service-name $(MERMAID_SERVICE) --output text | awk -F'/' '{print $$3}'))
	$(eval runtimeid=$(shell aws ecs describe-tasks --profile mermaid --cluster $(MERMAID_CLUSTER) --tasks $(taskid) | grep -oP '"runtimeId": "\K.+"' | head -c-2))
	$(eval localport=5444)
	aws ssm start-session \
		--profile mermaid \
		--target ecs:$(MERMAID_CLUSTER)_$(taskid)_$(runtimeid) \
		--document-name AWS-StartPortForwardingSessionToRemoteHost \
		--parameters '{"host":["$(MERMAID_DBHOST)"], "portNumber":["$(MERMAID_DBPORT)"], "localPortNumber":["$(localport)"]}'
