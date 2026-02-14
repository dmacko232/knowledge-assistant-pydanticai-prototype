# Backend

Backend service for Northwind Commerce Knowledge Assistant.

## Setup

This project uses `uv` for Python environment and dependency management.

```bash
# Install dependencies
uv sync

# Activate virtual environment (optional)
source .venv/bin/activate
```

## Development

### Linting and Formatting

```bash
# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Type Checking

```bash
# Run mypy
uv run mypy .
```

### Testing

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=. --cov-report=term-missing

# Run tests with verbose output
uv run pytest -v
```

## Project Structure

```
backend/
├── tests/          # Test files
├── pyproject.toml  # Project configuration and dependencies
└── README.md       # This file
```

## Configuration

- **Python Version**: >=3.11
- **Linter**: Ruff (configured in pyproject.toml)
- **Type Checker**: mypy (strict mode enabled)
- **Test Framework**: pytest with coverage

## CI/CD

See [../.github/workflows/backend.yml](../.github/workflows/backend.yml) for CI configuration.