.PHONY: install dev migrate migration test lint typecheck fmt clean

install:
	pip install -e ".[dev]"
	pre-commit install

dev:
	docker compose up -d
	sleep 2
	alembic upgrade head
	uvicorn clarke.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

test:
	pytest tests/ -v

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy clarke/

fmt:
	ruff format .
	ruff check --fix .

clean:
	docker compose down -v
