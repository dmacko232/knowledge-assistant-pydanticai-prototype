# Knowledge Assistant - PydanticAI Prototype

## Project Structure

- `src/data_pipeline/` — Batch CLI that ingests raw data into SQLite
  - `main.py` — CLI entry point (click-based)
  - `config.py` — Configuration and environment validation
  - `database/` — Storage layer (SQLite + sqlite-vec + FTS5)
  - `processors/` — Document, embedding, and structured data processors
  - `services/` — Embedding service (OpenAI)
  - `utils/` — Text and markdown utilities
- `src/backend/` — FastAPI REST API (PydanticAI agent, hybrid retrieval, chat history)
  - `main.py` — Presentation layer (routes)
  - `config.py` — pydantic-settings configuration
  - `agent.py` — PydanticAI agent factory + system prompt + tools
  - `models.py` — Pydantic request/response schemas
  - `use_cases/` — Business logic (ChatUseCase)
  - `services/` — Retrieval, SQL, chat history services
- `src/frontend/` — React chat UI (Vite + TypeScript + Tailwind CSS)
- `src/shared/` — Shared code, protocols/interfaces
- `tests/backend/` — Backend unit tests + acceptance tests (pytest)
- `tests/data_pipeline/` — Data pipeline unit tests (pytest)
- `docs/` — Design document and architecture docs
  - `architecture/backend.md` — Backend architecture documentation
  - `architecture/data_pipeline.md` — Data pipeline architecture documentation

## Commands

- `make check-all` — Run all quality checks and tests for both projects
- `make test-all` — Run all tests (data pipeline + backend + frontend)
- `make test` — Run data pipeline tests only
- `make test-backend` — Run backend tests only
- `make test-frontend` — Run frontend tests only
- `make quality-all` — Run quality checks for both projects
- `make test-acceptance` — Run acceptance tests against live backend
- `make dev` — Start backend + frontend together
- `make seed-demo` — Seed demo chats (requires running backend)

## Code Style

- **Imports**: Always use absolute imports, never relative
- **`__init__.py`**: Keep minimal (docstring only). Do NOT add `__all__` or re-export symbols. Consumers must import from the defining module directly (e.g., `from use_cases.chat import ChatUseCase`, not `from use_cases import ChatUseCase`)
- **Formatting**: Enforced by ruff — run `make format` / `make format-backend`
- **Linting**: Enforced by ruff with unsafe-fixes enabled
- **Data pipeline models**: SQLModel for database models
- **Backend models**: Pydantic BaseModel for API schemas; pydantic-settings for config
- **Database**: SQLite with sqlite-vec + FTS5 for knowledge DB; separate SQLite for chat history
- **Logging**: loguru in backend (no stdlib logging)
- **Tests**: All tests live in `tests/` at the project root (separate from source). `tests/backend/` and `tests/data_pipeline/` each have a `conftest.py` that adds the respective `src/` subdirectory to `sys.path`. Tests use absolute imports

## Documentation Maintenance

After making functional changes to the codebase, update the relevant docs:

- **`README.md`** — Setup instructions, project structure, available commands
- **`docs/architecture/backend.md`** — Backend structure, API endpoints, services, config, retrieval, tests
- **`docs/architecture/data_pipeline.md`** — Pipeline steps, DB schema, CLI commands, config

Skip doc updates for trivial changes (typos, internal refactors, test-only changes).
