.PHONY: help install install-dev test test-cov lint format type-check quality check-all clean run-pipeline reset-db stats

help:
	@echo "Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install        - Install data_pipeline dependencies"
	@echo "  make install-dev    - Install with dev dependencies (pytest, ruff, ty)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run ruff linter (auto-fixes issues)"
	@echo "  make format        - Format code with ruff"
	@echo "  make type-check    - Run ty type checker"
	@echo "  make quality       - Run all quality checks (format + lint + type-check)"
	@echo "  make check-all     - Run everything (quality + tests)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run unit tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo ""
	@echo "Pipeline:"
	@echo "  make run-pipeline  - Run the full data pipeline"
	@echo "  make run           - Shortcut for run-pipeline"
	@echo "  make reset-db      - Reset database (drop all tables)"
	@echo "  make stats         - Show database statistics"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Clean up generated files"
	@echo "  make check-env     - Validate configuration"

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
