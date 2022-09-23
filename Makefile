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
OS=$(shell sh -c 'uname 2>/dev/null || echo Unknown')

ifeq ($(OS), Linux)
	CURRENT_UID="1000:1000"
else
	CURRENT_UID="0:0"
endif


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

logs:
	@docker-compose logs -f $(API_SERVICE)

start:
	@make up

restart_api:
	@docker-compose restart api_service

# -----------------
# DB actions
# -----------------
dbbackup:
	@docker-compose run \
		--rm \
		--name api_dbbackup \
		-e AWS_ACCESS_KEY_ID=${OLD_AWS_ACCESS_KEY_ID} \
		-e AWS_SECRET_ACCESS_KEY=${OLD_AWS_SECRET_ACCESS_KEY} \
		-e PGPASSWORD=postgres \
		--entrypoint python \
		--user=$(CURRENT_UID) \
		$(API_SERVICE) \
		manage.py dbbackup local

dbrestore:
	@docker-compose run \
		--rm \
		--name api_dbrestore \
		-e AWS_ACCESS_KEY_ID=${OLD_AWS_ACCESS_KEY_ID} \
		-e AWS_SECRET_ACCESS_KEY=${OLD_AWS_SECRET_ACCESS_KEY} \
		-e PGPASSWORD=postgres \
		--entrypoint python \
		--user=$(CURRENT_UID) \
		$(API_SERVICE) \
		manage.py dbrestore local

migrate:
	@docker-compose run \
		--rm \
		--name api_migrate \
		--entrypoint python \
		--user=$(CURRENT_UID) \
		$(API_SERVICE) \
		manage.py migrate
# -----------------
# Setup actions
# -----------------
install:
	@echo "\n--- Shutting down existing stack ---\n"
	@make down
	@echo "\n--- Building new docker image ---\n"
	@make build
	@echo "\n--- Migrate ---\n"
	@make migrate
	@echo "\n--- Spinning up new stack ---\n"
	@make up

freshinstall:
	@echo "\n--- Shutting down existing stack ---\n"
	@make downnocache
	@echo "\n--- Building new docker image ---\n"
	@make buildnocache
	@echo "\n--- Migrate ---\n"
	@make migrate
	@echo "\n--- Spinning up new stack ---\n"
	@make up
	
# override the default entrypoint and use runserver (for development)
runserver:
	@docker-compose run \
		--rm \
		--name api_runserver \
		--workdir /code \
		--volume $(PWD)/src:/code \
		--publish 8080:8080 \
		--entrypoint python \
		--user=$(CURRENT_UID) \
		$(API_SERVICE) \
		manage.py runserver 0.0.0.0:8080

shell:
	@docker-compose exec \
		--user=$(CURRENT_UID) \
		api_service \
		bash

test:
	@docker-compose run \
		--rm \
		--name api_test \
		-e AWS_ACCESS_KEY_ID=${OLD_AWS_ACCESS_KEY_ID} \
		-e AWS_SECRET_ACCESS_KEY=${OLD_AWS_SECRET_ACCESS_KEY} \
		--entrypoint pytest \
		--user=$(CURRENT_UID) \
		$(API_SERVICE) \
		-v --no-migrations api/tests
