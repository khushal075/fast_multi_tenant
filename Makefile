# Makefile for Multi-tenant Platform

.PHONY: init migrate revision

# Start everything
up:
	docker compose up -d

# Start the database if not running
db-up:
	docker-compose up -d db

# Stop everything
down:
	docker compose down

# Generate new migration based on our model
revision:
	docker compose exec api poetry run alembic revision --autogenerate -m "$(msg)"

# Run all migration across all schemas
migrate:
	docker compose exec api poetry run alembic upgrade head

# Initialize the first tenant and basic data
seed:
	docker compose exec api python -m app.seed

# Follow the API logs
logs:
	docker compose logs -f api