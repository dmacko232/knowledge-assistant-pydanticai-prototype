# Knowledge Assistant - PydanticAI Prototype

## Project Structure

- `data_pipeline/` — Batch CLI that ingests raw data into SQLite
  - `main.py` — CLI entry point (click-based)
  - `config.py` — Configuration and environment validation
  - `database/` — Storage layer (SQLite + sqlite-vec + FTS5)
  - `processors/` — Document, embedding, and structured data processors
  - `services/` — Embedding service (OpenAI)
  - `utils/` — Text and markdown utilities
  - `tests/` — Unit tests (pytest)
- `backend/` — FastAPI REST API (PydanticAI agent, hybrid retrieval, chat history)
  - `main.py` — Presentation layer (routes)
  - `config.py` — pydantic-settings configuration
  - `agent.py` — PydanticAI agent factory + system prompt + tools
  - `models.py` — Pydantic request/response schemas
  - `use_cases/` — Business logic (ChatUseCase)
  - `services/` — Retrieval, SQL, chat history services
  - `tests/` — Unit tests (pytest)
- `docs/` — Design document and architecture docs
  - `architecture/backend.md` — Backend architecture documentation
  - `architecture/data_pipeline.md` — Data pipeline architecture documentation

## Commands

- `make check-all` — Run all quality checks and tests for both projects
- `make test-all` — Run all tests (data pipeline + backend)
- `make test` — Run data pipeline tests only
- `make test-backend` — Run backend tests only
- `make quality-all` — Run quality checks for both projects
- `make test-acceptance` — Run acceptance tests against live backend

## Code Style

- **Imports**: Always use absolute imports, never relative
- **Formatting**: Enforced by ruff — run `make format` / `make format-backend`
- **Linting**: Enforced by ruff with unsafe-fixes enabled
- **Data pipeline models**: SQLModel for database models
- **Backend models**: Pydantic BaseModel for API schemas; pydantic-settings for config
- **Database**: SQLite with sqlite-vec + FTS5 for knowledge DB; separate SQLite for chat history
- **Logging**: loguru in backend (no stdlib logging)
- **Tests**: pytest with fixtures in `conftest.py`. Tests use absolute imports

## Documentation Maintenance

After making functional changes to the codebase, update the relevant docs:

- **`README.md`** — Setup instructions, project structure, available commands
- **`docs/architecture/backend.md`** — Backend structure, API endpoints, services, config, retrieval, tests
- **`docs/architecture/data_pipeline.md`** — Pipeline steps, DB schema, CLI commands, config

Skip doc updates for trivial changes (typos, internal refactors, test-only changes).
