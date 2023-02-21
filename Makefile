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


down:
	@docker-compose down

downnocache:
	@docker-compose down -v

stop:
	@make down

buildnocache:
	$(eval short_sha=$(shell git rev-parse --short HEAD))
	@echo $(short_sha) > src/VERSION.txt
	@cat src/VERSION.txt
	@docker-compose build --no-cache --pull

build:
	$(eval short_sha=$(shell git rev-parse --short HEAD))
	@echo $(short_sha) > src/VERSION.txt
	@cat src/VERSION.txt
	@docker-compose build

up:
	docker-compose up -d

start:
	@make up

logs:
	@docker-compose logs -f $(API_SERVICE)

dbbackup:
	@docker-compose exec $(API_SERVICE) python manage.py dbbackup local

dbrestore:
	@docker-compose exec $(API_SERVICE) python manage.py dbrestore local

migrate:
	@docker-compose exec $(API_SERVICE) python manage.py migrate

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
	@docker-compose exec $(API_SERVICE) python manage.py runserver 0.0.0.0:8080

shellplus:
	@docker-compose exec $(API_SERVICE) python manage.py shell_plus

shell:
	@docker-compose exec $(API_SERVICE) /bin/bash

shellroot:
	@docker-compose exec --user=root $(API_SERVICE) /bin/bash

shellplusroot:
	@docker-compose exec --user=root $(API_SERVICE) python manage.py shell_plus

test:
	@docker-compose exec $(API_SERVICE) pytest -v --no-migrations --rich api/tests

# -----------------
# Fargate Maintenance (docker exec)
# -----------------
# Assume local profile name in ~/.aws/config is `mermaid`

# TODO: populate service-name dynamically, using dev/prod arg passed in from commandline like `make env=dev cloud_shell`
# Some way to wrap in `su webapp` and then `bash`?
cloudshell:
	$(eval cluster=mermaid-api-infra-common-MermaidApiClusterB0854EC6-xitj9XbqTwap)
	$(eval service=dev-mermaid-api-django-FargateServiceAC2B3B85-bxgJi3aV1CQd)
	$(eval taskid=$(shell aws ecs list-tasks --profile mermaid --cluster $(cluster) --service-name $(service) --output text | awk -F'/' '{print $$3}'))
	aws ecs execute-command  \
		--profile mermaid \
		--cluster mermaid-api-infra-common-MermaidApiClusterB0854EC6-xitj9XbqTwap \
		--task $(taskid) \
		--container MermaidAPI \
		--command "/bin/bash" \
		--interactive

cloudtunnel:
	$(eval cluster=mermaid-api-infra-common-MermaidApiClusterB0854EC6-xitj9XbqTwap)
	$(eval service=dev-mermaid-api-django-FargateServiceAC2B3B85-bxgJi3aV1CQd)
	$(eval taskid=$(shell aws ecs list-tasks --profile mermaid --cluster $(cluster) --service-name $(service) --output text | awk -F'/' '{print $$3}'))
	$(eval runtimeid=$(shell aws ecs describe-tasks --profile mermaid --cluster $(cluster) --tasks $(taskid) | grep -oP '"runtimeId": "\K.+"' | head -c-2))
	$(eval dbhost=mermaid-api-infra-common-postgresrdsv2b4b63a33-576a8t2dqako.cus0vfcwxkgi.us-east-1.rds.amazonaws.com)
	$(eval localport=5444)
	aws ssm start-session \
		--profile mermaid \
		--target ecs:$(cluster)_$(taskid)_$(runtimeid) \
		--document-name AWS-StartPortForwardingSessionToRemoteHost \
		--parameters '{"host":["$(dbhost)"], "portNumber":["5432"], "localPortNumber":["$(localport)"]}'
