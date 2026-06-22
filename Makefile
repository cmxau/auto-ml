.PHONY: up down logs migrate test-backend shell-backend create-bucket

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f backend worker

migrate:
	docker compose run --rm backend alembic upgrade head

test-backend:
	docker compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

shell-backend:
	docker compose exec backend bash

create-bucket:
	docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin && \
	docker compose exec minio mc mb local/automl-files || true
