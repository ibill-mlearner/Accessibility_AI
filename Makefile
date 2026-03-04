.PHONY: up down logs reset

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

# Resets only local Docker Compose volumes for this project.
reset:
	docker compose down -v
