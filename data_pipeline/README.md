# Data Pipeline

Data pipeline for Northwind Commerce Knowledge Assistant.

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
```

## Project Structure

```
data_pipeline/
├── tests/          # Test files
├── pyproject.toml  # Project configuration and dependencies
└── README.md       # This file
```

## Configuration

- **Python Version**: >=3.12
- **Linter**: Ruff (configured in pyproject.toml)
- **Type Checker**: mypy (strict mode enabled)
- **Test Framework**: pytest with coverage

## CI/CD

See [../.github/workflows/data-pipeline.yml](../.github/workflows/data-pipeline.yml) for CI configuration.
