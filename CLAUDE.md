# Knowledge Assistant - PydanticAI Prototype

## Project Structure

- `data_pipeline/` — Main Python package (run from this directory)
  - `main.py` — CLI entry point (click-based)
  - `config.py` — Configuration and environment validation
  - `database/` — Storage layer (SQLite + sqlite-vec + FTS5)
  - `processors/` — Document, embedding, and structured data processors
  - `services/` — Embedding service (OpenAI)
  - `utils/` — Text and markdown utilities
  - `tests/` — Unit tests (pytest)
- `docs/` — Design documents

## Commands

- `make check-all` — Run all quality checks and tests (format + lint + type-check + test)
- `make test` — Run unit tests only
- `make quality` — Run format + lint + type-check only
- `make type-check` — Run ty type checker only
- `make lint` — Run ruff linter with auto-fix
- `make format` — Run ruff formatter

All make targets run from the `data_pipeline/` directory automatically.

## Code Style

- **Imports**: Always use absolute imports (e.g., `from database.models import ...`), never relative imports (e.g., `from .models import ...`)
- **Formatting**: Enforced by ruff — run `make format`
- **Linting**: Enforced by ruff with unsafe-fixes enabled
- **Type checking**: Enforced by ty (red-knot) — all code must pass `make type-check`
- **Models**: Use SQLModel for database models. Non-table models (like `SearchResult`) use `SQLModel` without `table=True`
- **Database**: SQLite with sqlite-vec for vector search and FTS5 for full-text search. Embeddings must be serialized with `serialize_float32()` before passing to sqlite
- **Tests**: pytest with fixtures in `conftest.py`. Tests use absolute imports matching the source code