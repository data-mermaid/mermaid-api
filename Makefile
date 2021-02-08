
down:
	@docker-compose down

build_image:
	@docker-compose build --no-cache --pull

up:
	@docker-compose up -d

dbrestore:
	@docker exec -it api_service python manage.py dbrestore local

migrate:
	@docker exec -it api_service python manage.py migrate

fresh_install:
	@echo "\n--- Shutting down existing stack ---\n"
	@make down
	@echo "\n--- Building new docker image ---\n"
	@make build_image
	@make up
	@echo "\n--- Spinning up new stack ---\n"
	@sleep 20
	@echo "\n--- Restoring MERMAID database ---\n"
	@make dbrestore
	@echo "\n--- Applying MERMAID database migrations ---\n"
	@make migrate

runserver:
	@docker exec -it api_service python manage.py runserver 0.0.0.0:8080

shell:
	@docker exec -it api_service /bin/bash
