.PHONY: install dev test lint fmt clean docker-build docker-up docker-down help

PYTHON := python3
PIP := pip
PYTEST := pytest
ROOF := ruff

install:
	$(PIP) install -e ".[dev]"

dev:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8080

test:
	$(PYTEST) -v --cov=. --cov-report=term-missing --cov-report=html

test-coverage:
	$(PYTEST) --cov=. --cov-report=term-missing --cov-report=html

clean:
	rm -rf .pytest_cache .coverage htmlcov coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

lint:
	$(ROOF) check .

fmt:
	$(ROOF) format .

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(MESSAGE)"

docker-build:
	docker build -t wittyhub/api -f deploy/docker/Dockerfile .

docker-up:
	docker-compose -f deploy/docker/docker-compose.yaml up -d

docker-down:
	docker-compose -f deploy/docker/docker-compose.yaml down

docker-logs:
	docker-compose -f deploy/docker/docker-compose.yaml logs -f

help:
	@echo "Available targets:"
	@echo "  install       - Install dependencies (including dev)"
	@echo "  dev           - Run development server with hot reload"
	@echo "  test          - Run tests with coverage"
	@echo "  test-coverage - Generate HTML coverage report"
	@echo "  clean         - Clean cache and coverage files"
	@echo "  lint          - Run ruff linter"
	@echo "  fmt           - Format code with ruff"
	@echo "  migrate       - Run database migrations"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-up     - Start Docker services"
	@echo "  docker-down   - Stop Docker services"