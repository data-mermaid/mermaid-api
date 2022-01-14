# Makefile Readme
# ----------------
#
# down: shut down docker containers (database and api containers).
# buildnocache: build new docker image without using cache.
# up: start docker containers (database and api containers).
# dbbackup: create a backup of your local database and push to S3.  NOTE: Local backs are used by all devs during database restore.
# dbrestore: restore a back from s3 to your local database.
# migrate: apply any database migrations to local database.
# freshinstall:  helper command that wraps server commands to setup API, database and data locally.
# runserver: Start api web server, runs on http://localhost:8080/
# shell: Starts bash terminal inside the API docker container.
# 
# 
# To get start run `make freshinstall`
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

buildnocache:
	./ci_cd/version.sh
	@docker-compose build --no-cache --pull

up:
	docker-compose up -d	

dbbackup:
	@docker-compose exec --user=$(CURRENT_UID) $(API_SERVICE) python manage.py dbbackup local

dbrestore:
	@docker-compose exec --user=$(CURRENT_UID) $(API_SERVICE) python manage.py dbrestore local

migrate:
	@docker-compose exec --user=$(CURRENT_UID) $(API_SERVICE) python manage.py migrate

install:
	@echo "\n--- Shutting down existing stack ---\n"
	@make down
	@echo "\n--- Building new docker image ---\n"
	@make buildnocache
	@make up
	@echo "\n--- Spinning up new stack ---\n"
	@sleep 20
	@echo "\n--- Applying MERMAID database migrations ---\n"
	@make migrate


freshinstall:
	@echo "\n--- Shutting down existing stack ---\n"
	@make down
	@echo "\n--- Building new docker image ---\n"
	@make buildnocache
	@make up
	@echo "\n--- Spinning up new stack ---\n"
	@sleep 20
	@echo "\n--- Restoring MERMAID database ---\n"
	@make dbrestore
	@echo "\n--- Applying MERMAID database migrations ---\n"
	@make migrate

runserver:
	@docker-compose exec --user=$(CURRENT_UID) $(API_SERVICE) python manage.py runserver 0.0.0.0:8080

shell:
	@docker-compose exec --user=$(CURRENT_UID) $(API_SERVICE) /bin/bash

test:
	@docker-compose exec --user=$(CURRENT_UID) $(API_SERVICE) pytest -v --no-migrations api/tests