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
	./ci_cd/version.sh
	@docker-compose build --no-cache --pull

build:
	./ci_cd/version.sh
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
	@docker-compose exec $(API_SERVICE) pytest -v --no-migrations api/tests

# -----------------
# Fargate Maintenance (docker exec)
# -----------------
# TODO: populate service-name dynamically, using dev/prod arg passed in from commandline like `make env=dev cloud_shell`
# Maybe specify --profile? Maybe wrap in `su webapp` and then `bash`?

cloud_shell:
	$(eval taskid=$(shell aws ecs list-tasks --region us-east-1 --cluster mermaid-api-infra-common-MermaidApiClusterB0854EC6-xitj9XbqTwap --service-name dev-mermaid-api-django-FargateServiceAC2B3B85-BifBKQE0PkAo --output text | awk -F'/' '{print $$3}'))
	aws ecs execute-command  \
		--region us-east-1 \
		--cluster mermaid-api-infra-common-MermaidApiClusterB0854EC6-xitj9XbqTwap \
		--task $(taskid) \
		--container MermaidAPI \
		--command "/bin/bash" \
		--interactive
