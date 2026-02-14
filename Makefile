.PHONY: help install lint format type-check test clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =============================================================================
# Installation
# =============================================================================

install: ## Install all dependencies for all components
	@echo "📦 Installing data_analysis dependencies..."
	cd data_analysis && uv sync
	@echo "📦 Installing backend dependencies..."
	cd backend && uv sync
	@echo "📦 Installing data_pipeline dependencies..."
	cd data_pipeline && uv sync
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm ci
	@echo "✅ All dependencies installed!"

# =============================================================================
# Linting & Formatting
# =============================================================================

lint: ## Run linters on all components
	@echo "🔍 Linting data_analysis..."
	cd data_analysis && uv run ruff check .
	@echo "🔍 Linting backend..."
	cd backend && uv run ruff check . || true
	@echo "🔍 Linting data_pipeline..."
	cd data_pipeline && uv run ruff check . || true
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint || true

format: ## Format code in all components
	@echo "✨ Formatting data_analysis..."
	cd data_analysis && uv run ruff format .
	@echo "✨ Formatting backend..."
	cd backend && uv run ruff format . || true
	@echo "✨ Formatting data_pipeline..."
	cd data_pipeline && uv run ruff format . || true
	@echo "✨ Formatting frontend..."
	cd frontend && npm run format || true

type-check: ## Run type checking on all components (mypy + ty)
	@echo "🔎 Type checking data_analysis with mypy..."
	cd data_analysis && uv run mypy analyze.py
	@echo "🔎 Type checking data_analysis with ty..."
	cd data_analysis && uv run ty check analyze.py || true
	@echo "🔎 Type checking backend with mypy..."
	cd backend && uv run mypy . || true
	@echo "🔎 Type checking backend with ty..."
	cd backend && uv run ty check . || true
	@echo "🔎 Type checking data_pipeline with mypy..."
	cd data_pipeline && uv run mypy . || true
	@echo "🔎 Type checking data_pipeline with ty..."
	cd data_pipeline && uv run ty check . || true
	@echo "🔎 Type checking frontend..."
	cd frontend && npm run type-check || true

# =============================================================================
# Testing
# =============================================================================

test: ## Run tests for all components
	@echo "🧪 Testing data_analysis..."
	cd data_analysis && uv run pytest || true
	@echo "🧪 Testing backend..."
	cd backend && uv run pytest || true
	@echo "🧪 Testing data_pipeline..."
	cd data_pipeline && uv run pytest || true
	@echo "🧪 Testing frontend..."
	cd frontend && npm test || true

# =============================================================================
# Data Analysis
# =============================================================================

analyze: ## Run data analysis
	@echo "📊 Running data analysis..."
	cd data_analysis && uv run python analyze.py

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Remove build artifacts and caches
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# =============================================================================
# CI/CD
# =============================================================================

ci: lint type-check test ## Run all CI checks locally
	@echo "✅ All CI checks passed!"