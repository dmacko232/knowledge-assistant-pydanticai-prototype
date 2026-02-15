.PHONY: help install install-dev test test-cov lint format type-check quality check-all clean \
       run-pipeline reset-db stats run-backend test-backend install-backend install-backend-dev \
       lint-backend format-backend test-acceptance \
       docker-build docker-pipeline docker-backend docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install              - Install data_pipeline dependencies"
	@echo "  make install-dev          - Install data_pipeline with dev dependencies"
	@echo "  make install-backend      - Install backend dependencies"
	@echo "  make install-backend-dev  - Install backend with dev dependencies"
	@echo "  make install-all          - Install everything"
	@echo ""
	@echo "Code Quality (data_pipeline):"
	@echo "  make lint          - Run ruff linter (auto-fixes issues)"
	@echo "  make format        - Format code with ruff"
	@echo "  make type-check    - Run ty type checker"
	@echo "  make quality       - Run all quality checks (format + lint + type-check)"
	@echo "  make check-all     - Run everything (quality + tests)"
	@echo ""
	@echo "Code Quality (backend):"
	@echo "  make lint-backend   - Run ruff linter on backend"
	@echo "  make format-backend - Format backend code with ruff"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run data_pipeline unit tests"
	@echo "  make test-cov        - Run data_pipeline tests with coverage"
	@echo "  make test-backend    - Run backend unit tests"
	@echo "  make test-all        - Run all tests"
	@echo "  make test-acceptance - Run acceptance tests (requires running backend)"
	@echo ""
	@echo "Pipeline:"
	@echo "  make run-pipeline  - Run the full data pipeline"
	@echo "  make reset-db      - Reset database (drop all tables)"
	@echo "  make stats         - Show database statistics"
	@echo ""
	@echo "Backend:"
	@echo "  make run-backend   - Start the FastAPI backend server"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    - Build all Docker images"
	@echo "  make docker-pipeline - Run data pipeline in Docker"
	@echo "  make docker-backend  - Start backend in Docker"
	@echo "  make docker-up       - Run pipeline then start backend"
	@echo "  make docker-down     - Stop all Docker containers"
	@echo "  make docker-logs     - Tail backend logs"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Clean up generated files"
	@echo "  make check-env     - Validate data_pipeline configuration"

# ---------------------------------------------------------------------------
# Data Pipeline
# ---------------------------------------------------------------------------

install:
	cd data_pipeline && pip install -e .

install-dev:
	cd data_pipeline && pip install -e ".[dev]"

lint:
	cd data_pipeline && uv run ruff check --fix --unsafe-fixes .

format:
	cd data_pipeline && uv run ruff format .

type-check:
	cd data_pipeline && uv sync --extra dev && uv run ty check

quality: format lint type-check
	@echo "✓ All quality checks passed!"

check-all: quality test
	@echo "✓ All checks passed (quality + tests)!"

test:
	cd data_pipeline && uv run pytest

test-cov:
	cd data_pipeline && uv run pytest --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report: data_pipeline/htmlcov/index.html"

run-pipeline:
	cd data_pipeline && python main.py process-all

reset-db:
	cd data_pipeline && python main.py reset

stats:
	cd data_pipeline && python main.py stats

check-env:
	cd data_pipeline && python -c "import config; config.validate_config()"

# Shortcut
run: run-pipeline

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

install-backend:
	cd backend && pip install -e .

install-backend-dev:
	cd backend && pip install -e ".[dev]"

lint-backend:
	cd backend && uv run ruff check --fix --unsafe-fixes .

format-backend:
	cd backend && uv run ruff format .

test-backend:
	cd backend && uv run pytest

run-backend:
	cd backend && python main.py

# ---------------------------------------------------------------------------
# All
# ---------------------------------------------------------------------------

install-all: install install-backend

test-all: test test-backend
	@echo "✓ All tests passed!"

test-acceptance:
	python acceptance_tests.py

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

docker-build:
	docker compose build

docker-pipeline:
	docker compose run --rm data-pipeline

docker-backend:
	docker compose up backend

docker-up:
	docker compose up

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ty_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf database/*.sqlite 2>/dev/null || true
	@echo "✓ Cleanup complete"
