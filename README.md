# Northwind Commerce — Knowledge Assistant

An internal knowledge assistant for the fictional **Northwind Commerce** company. Employees can ask questions about policies, runbooks, domain documentation, KPIs, and the team directory — and receive grounded, cited answers backed by the internal knowledge base.

## Architecture

The project has four components:

```
├── src/
│   ├── data_pipeline/   # Ingest & index raw documents and structured data
│   ├── backend/         # FastAPI + PydanticAI agent that answers questions
│   ├── frontend/        # React chat UI (Vite + TypeScript + Tailwind CSS)
│   └── shared/          # Shared protocols and constants
├── tests/
│   ├── backend/         # Backend unit + acceptance tests
│   └── data_pipeline/   # Data pipeline unit tests
└── data/                # Raw knowledge base (markdown, CSV, JSON)
```

### Data Pipeline
Processes markdown documents into chunked, embedded vectors (SQLite + sqlite-vec) and loads structured data (KPIs, employee directory) into relational tables. Produces a single SQLite database consumed by the backend.

### Backend
A FastAPI server powered by a PydanticAI agent with two tools:
- **Knowledge Base Search** — hybrid retrieval (vector + BM25) with Reciprocal Rank Fusion reranking
- **Structured Data Lookup** — read-only SQL queries against KPI catalog and employee directory

The agent is prompt-engineered to ground every answer in retrieved sources, include `[1]`, `[2]` citations, prefer newer/authoritative documents, and refuse to answer when the KB lacks relevant information.

JWT authentication is built in and toggleable via `AUTH_ENABLED` (default: `true`). When disabled, a mock user is injected for development.

OpenTelemetry instrumentation is built in and toggleable via `OTEL_ENABLED` (default: `false`). When enabled, traces are emitted for all HTTP requests and PydanticAI agent calls.

### Frontend
A React single-page application providing a ChatGPT-like chat interface. Features include:
- Login screen with name/email authentication
- Sidebar with chat history and "New Chat" button
- Streaming responses with real-time token rendering
- LLM-generated chat titles (triggered after the first assistant reply)
- Markdown rendering with inline citations and collapsible sources
- Tool call visibility for transparency

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Azure OpenAI API access (for embeddings and chat)

### 1. Run the Data Pipeline

```bash
# Install dependencies
make install

# Configure Azure OpenAI credentials
cp src/data_pipeline/.env.example src/data_pipeline/.env
# Edit src/data_pipeline/.env with your API key and endpoints

# Process all documents and structured data
make run-pipeline
```

### 2. Start the Backend

```bash
# Install backend dependencies
make install-backend

# Configure backend credentials
cp src/backend/.env.example src/backend/.env
# Edit src/backend/.env with your API key and endpoints

# Start the FastAPI server (http://localhost:8000)
make run-backend
```

### 3. Start the Frontend

```bash
# Install frontend dependencies
make install-frontend

# Start the dev server (http://localhost:3000)
make run-frontend
```

The frontend proxies `/api/*` requests to the backend at `localhost:8000` during development.

### 4. Try It Out

Open [http://localhost:3000](http://localhost:3000) in your browser, sign in with any name/email, and start asking questions.

API docs are also available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Docker

Run everything with Docker Compose — no local Python or Node.js install needed.

```bash
# Configure credentials
cp src/data_pipeline/.env.example src/data_pipeline/.env
cp src/backend/.env.example src/backend/.env
# Edit both .env files with your Azure OpenAI credentials

# Build images, run pipeline, start backend + frontend
make docker-up

# Or run steps individually:
make docker-build       # Build images
make docker-pipeline    # Run data pipeline (one-off)
make docker-backend     # Start backend server
make docker-frontend    # Start frontend server
make docker-down        # Stop everything
```

- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Frontend UI:** [http://localhost:3000](http://localhost:3000)

## Development

```bash
# Install everything with dev dependencies
make install-dev
make install-backend-dev
make install-frontend

# Run all tests
make test-all

# Code quality (data_pipeline)
make quality

# Code quality (backend)
make quality-backend

# Run everything: quality + tests
make check-all
```

Run `make help` to see all available commands.

## Project Structure

```
knowledge-assistant-pydanticai-prototype/
├── src/
│   ├── data_pipeline/             # Ingestion & indexing pipeline
│   │   ├── main.py                # CLI entry point
│   │   ├── config.py              # Configuration
│   │   ├── database/              # Vector store + relational store
│   │   ├── processors/            # Document chunking, embedding, structured parsing
│   │   ├── services/              # Azure OpenAI embedding service
│   │   └── utils/                 # Text & markdown utilities
│   ├── backend/                   # FastAPI + PydanticAI backend
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── config.py              # Configuration (pydantic-settings)
│   │   ├── agent.py               # PydanticAI agent with tools & system prompt
│   │   ├── auth.py                # JWT authentication helpers
│   │   ├── telemetry.py           # OpenTelemetry setup (OTEL_ENABLED toggle)
│   │   ├── models.py              # API request/response schemas
│   │   ├── use_cases/             # Business logic (ChatUseCase)
│   │   └── services/              # Retrieval, SQL, chat history services
│   ├── frontend/                  # React chat UI
│   │   ├── src/
│   │   │   ├── App.tsx            # Router + auth context
│   │   │   ├── api.ts             # API client with JWT injection
│   │   │   ├── auth.ts            # Auth helpers + context
│   │   │   ├── pages/             # Login, Chat
│   │   │   └── components/        # Sidebar, MessageList, ChatInput, etc.
│   │   ├── Dockerfile             # Multi-stage build (Node → nginx)
│   │   └── nginx.conf             # Reverse proxy config for /api
│   └── shared/                    # Shared protocols and constants
│       └── protocols/             # Service interface definitions
├── tests/
│   ├── backend/                   # Backend unit + acceptance tests
│   └── data_pipeline/             # Data pipeline unit tests
├── data/
│   └── raw/
│       ├── documents/             # Markdown KB (domain/, policies/, runbooks/)
│       └── structured/            # kpi_catalog.csv, directory.json
├── database/                      # Generated SQLite database (after pipeline run)
├── docs/                          # Design document, architecture docs, diagrams
├── docker-compose.yml             # Docker Compose for running the full stack
└── Makefile                       # All build, test, run, and Docker commands
```
