# Northwind Commerce — Knowledge Assistant

An internal knowledge assistant for the fictional **Northwind Commerce** company. Employees can ask questions about policies, runbooks, domain documentation, KPIs, and the team directory — and receive grounded, cited answers backed by the internal knowledge base.

## Architecture

The project has three components:

```
├── data_pipeline/   # Ingest & index raw documents and structured data
├── backend/         # FastAPI + PydanticAI agent that answers questions
└── data/            # Raw knowledge base (markdown, CSV, JSON)
```

### Data Pipeline
Processes markdown documents into chunked, embedded vectors (SQLite + sqlite-vec) and loads structured data (KPIs, employee directory) into relational tables. Produces a single SQLite database consumed by the backend.

### Backend
A FastAPI server powered by a PydanticAI agent with two tools:
- **Knowledge Base Search** — hybrid retrieval (vector + BM25) with Reciprocal Rank Fusion reranking
- **Structured Data Lookup** — read-only SQL queries against KPI catalog and employee directory

The agent is prompt-engineered to ground every answer in retrieved sources, include `[1]`, `[2]` citations, prefer newer/authoritative documents, and refuse to answer when the KB lacks relevant information.

## Quick Start

### Prerequisites
- Python 3.11+
- Azure OpenAI API access (for embeddings and chat)

### 1. Run the Data Pipeline

```bash
# Install dependencies
make install

# Configure Azure OpenAI credentials
cp data_pipeline/.env.example data_pipeline/.env
# Edit data_pipeline/.env with your API key and endpoints

# Process all documents and structured data
make run-pipeline
```

### 2. Start the Backend

```bash
# Install backend dependencies
make install-backend

# Configure backend credentials
cp backend/.env.example backend/.env
# Edit backend/.env with your API key and endpoints

# Start the FastAPI server (http://localhost:8000)
make run-backend
```

### 3. Try It Out

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is the security policy for production access?"}]}'
```

API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Docker

Run everything with Docker Compose — no local Python install needed.

```bash
# Configure credentials
cp data_pipeline/.env.example data_pipeline/.env
cp backend/.env.example backend/.env
# Edit both .env files with your Azure OpenAI credentials

# Build images, run pipeline, then start backend
make docker-up

# Or run steps individually:
make docker-build       # Build images
make docker-pipeline    # Run data pipeline (one-off)
make docker-backend     # Start backend server
make docker-down        # Stop everything
```

The backend is available at [http://localhost:8000](http://localhost:8000) once running.

## Development

```bash
# Install everything with dev dependencies
make install-dev
make install-backend-dev

# Run all tests
make test-all

# Code quality (data_pipeline)
make quality

# Code quality (backend)
make lint-backend && make format-backend
```

Run `make help` to see all available commands.

## Project Structure

```
knowledge-assistant-pydanticai-prototype/
├── data/
│   └── raw/
│       ├── documents/         # Markdown KB (domain/, policies/, runbooks/)
│       └── structured/        # kpi_catalog.csv, directory.json
├── data_pipeline/             # Ingestion & indexing pipeline
│   ├── main.py                # CLI entry point
│   ├── config.py              # Configuration
│   ├── database/              # Vector store + relational store
│   ├── processors/            # Document chunking, embedding, structured parsing
│   ├── services/              # Azure OpenAI embedding service
│   ├── utils/                 # Text & markdown utilities
│   └── tests/                 # Pipeline unit tests
├── backend/                   # FastAPI + PydanticAI backend
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # Configuration
│   ├── agent.py               # PydanticAI agent with tools & system prompt
│   ├── models.py              # API request/response schemas
│   ├── services/              # Retrieval service, SQL service
│   └── tests/                 # Backend unit tests
├── database/                  # Generated SQLite database (after pipeline run)
├── docs/                      # Design document, architecture docs, diagrams
├── docker-compose.yml         # Docker Compose for running the full stack
└── Makefile                   # All build, test, run, and Docker commands
```
