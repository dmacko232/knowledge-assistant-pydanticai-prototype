.PHONY: help install install-dev test test-cov lint format type-check quality check-all clean \
       run-pipeline reset-db stats run-backend test-backend install-backend install-backend-dev \
       lint-backend format-backend quality-backend quality-all test-acceptance \
       install-frontend run-frontend test-frontend lint-frontend typecheck-frontend quality-frontend \
       dev seed-demo \
       docker-build docker-pipeline docker-backend docker-frontend docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install              - Install data_pipeline dependencies"
	@echo "  make install-dev          - Install data_pipeline with dev dependencies"
	@echo "  make install-backend      - Install backend dependencies"
	@echo "  make install-backend-dev  - Install backend with dev dependencies"
	@echo "  make install-frontend     - Install frontend dependencies"
	@echo "  make install-all          - Install everything"
	@echo ""
	@echo "Code Quality (data_pipeline):"
	@echo "  make lint          - Run ruff linter (auto-fixes issues)"
	@echo "  make format        - Format code with ruff"
	@echo "  make type-check    - Run ty type checker"
	@echo "  make quality       - Run data_pipeline quality checks (format + lint + type-check)"
	@echo ""
	@echo "Code Quality (backend):"
	@echo "  make lint-backend    - Run ruff linter on backend"
	@echo "  make format-backend  - Format backend code with ruff"
	@echo "  make quality-backend - Run backend quality checks (format + lint)"
	@echo ""
	@echo "Code Quality (frontend):"
	@echo "  make lint-frontend      - Run ESLint on frontend"
	@echo "  make typecheck-frontend - Run TypeScript type check"
	@echo "  make quality-frontend   - Run frontend quality checks (lint + typecheck)"
	@echo ""
	@echo "Code Quality (all):"
	@echo "  make quality-all   - Run quality checks for all projects"
	@echo "  make check-all     - Run everything (quality + tests for all projects)"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run data_pipeline unit tests"
	@echo "  make test-cov        - Run data_pipeline tests with coverage"
	@echo "  make test-backend    - Run backend unit tests"
	@echo "  make test-frontend   - Run frontend unit tests"
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
	@echo "Frontend:"
	@echo "  make run-frontend  - Start the React dev server (port 3000)"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start backend + frontend together"
	@echo "  make seed-demo     - Seed demo chats (requires running backend)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    - Build all Docker images"
	@echo "  make docker-pipeline - Run data pipeline in Docker"
	@echo "  make docker-backend  - Start backend in Docker"
	@echo "  make docker-frontend - Start frontend in Docker"
	@echo "  make docker-up       - Run pipeline, backend, and frontend"
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
	cd src/data_pipeline && pip install -e .

install-dev:
	cd src/data_pipeline && pip install -e ".[dev]"

lint:
	cd src/data_pipeline && uv run ruff check --fix --unsafe-fixes .

format:
	cd src/data_pipeline && uv run ruff format .

type-check:
	cd src/data_pipeline && uv sync --extra dev && uv run ty check

quality: format lint type-check
	@echo "✓ Data pipeline quality checks passed!"

check-all: quality-all test-all
	@echo "✓ All checks passed (quality + tests for all projects)!"

test:
	cd src/data_pipeline && uv run python -m pytest ../../tests/data_pipeline

test-cov:
	cd src/data_pipeline && uv run python -m pytest ../../tests/data_pipeline --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report: src/data_pipeline/htmlcov/index.html"

run-pipeline:
	cd src/data_pipeline && python main.py process-all

reset-db:
	cd src/data_pipeline && python main.py reset

stats:
	cd src/data_pipeline && python main.py stats

check-env:
	cd src/data_pipeline && python -c "import config; config.validate_config()"

# Shortcut
run: run-pipeline

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

install-backend:
	cd src/backend && pip install -e .

install-backend-dev:
	cd src/backend && pip install -e ".[dev]"

lint-backend:
	cd src/backend && uv run ruff check --fix --unsafe-fixes .

format-backend:
	cd src/backend && uv run ruff format .

quality-backend: format-backend lint-backend
	@echo "✓ Backend quality checks passed!"

test-backend:
	cd src/backend && uv run python -m pytest ../../tests/backend -k "not acceptance"

run-backend:
	cd src/backend && python main.py

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

install-frontend:
	cd src/frontend && npm install

run-frontend:
	cd src/frontend && npm run dev

test-frontend:
	cd src/frontend && npm test

lint-frontend:
	cd src/frontend && npm run lint

typecheck-frontend:
	cd src/frontend && npm run typecheck

quality-frontend: lint-frontend typecheck-frontend
	@echo "✓ Frontend quality checks passed!"

# ---------------------------------------------------------------------------
# Dev (run both backend + frontend)
# ---------------------------------------------------------------------------

dev:
	@echo "Starting backend (port 8000) and frontend (port 3000)..."
	@trap 'kill 0' INT TERM; \
	(cd src/backend && python main.py) & \
	(cd src/frontend && npm run dev) & \
	wait

seed-demo:
	python scripts/seed_demo.py

# ---------------------------------------------------------------------------
# All
# ---------------------------------------------------------------------------

quality-all: quality quality-backend quality-frontend
	@echo "✓ All quality checks passed!"

install-all: install install-backend install-frontend

test-all: test test-backend test-frontend
	@echo "✓ All tests passed!"

test-acceptance:
	python tests/backend/test_acceptance.py

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

docker-build:
	docker compose build

docker-pipeline:
	docker compose run --rm data-pipeline

docker-backend:
	docker compose up backend

docker-frontend:
	docker compose up frontend

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
