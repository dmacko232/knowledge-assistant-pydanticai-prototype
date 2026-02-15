# Data Pipeline

Ingestion pipeline that processes the Northwind Commerce internal knowledge base into a queryable SQLite database. It handles both unstructured documents (markdown) and structured data (CSV/JSON).

## What It Does

1. **Document Processing** — reads markdown files from `data/raw/documents/`, chunks them by structure (headers), and generates embeddings via Azure OpenAI.
2. **Structured Data Processing** — parses `kpi_catalog.csv` and `directory.json` into relational tables.
3. **Storage** — writes everything into a single SQLite database at `database/knowledge_assistant.sqlite`, using:
   - **sqlite-vec** for vector similarity search
   - **FTS5** for BM25 keyword search
   - **SQLModel** tables for KPIs and employees

## Setup

### 1. Install Dependencies

```bash
cd data_pipeline
pip install -e .

# Or with dev tools (pytest, ruff, ty):
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI API key and endpoint
```

### 3. Run

```bash
# From the project root:
make run-pipeline

# Or directly:
python main.py process-all

# Without API keys (mock embeddings for testing):
python main.py process-all --mock-embeddings
```

## CLI Reference

| Command | Description |
|---|---|
| `python main.py process-all [--mock-embeddings]` | Run the full pipeline |
| `python main.py process-documents [--mock-embeddings]` | Process documents only |
| `python main.py process-structured` | Process structured data only |
| `python main.py stats` | Show database statistics |
| `python main.py reset` | Drop all tables and reset |
| `python main.py dump-db [--sample N] [--schema]` | Inspect database contents |
| `python main.py search-vector "query" [--limit N] [--category CAT]` | Semantic search |
| `python main.py search-bm25 "query" [--limit N] [--category CAT]` | Keyword search |

## Database Schema

### Vector Store

| Table | Purpose |
|---|---|
| `document_chunks` | Chunk text, metadata, document name, category, section header |
| `vec_chunks` | Embedding vectors (1536-dim, sqlite-vec) |
| `fts_chunks` | Full-text search index (FTS5 with Porter stemming) |

### Relational Store

| Table | Columns |
|---|---|
| `kpi_catalog` | kpi_name, definition, owner_team, primary_source, last_updated |
| `directory` | name, email, team, role, timezone |

## Architecture

```
data_pipeline/
├── main.py                  # Click CLI entry point
├── config.py                # Paths, Azure OpenAI settings, chunking params
├── database/
│   ├── models.py            # SQLModel table definitions
│   ├── interfaces.py        # Protocol interfaces
│   ├── vector_store.py      # Vector DB (sqlite-vec + FTS5)
│   └── relational_store.py  # KPI & employee tables
├── processors/
│   ├── document_processor.py    # Markdown → chunks
│   ├── embedding_processor.py   # Chunks → embeddings
│   └── structured_processor.py  # CSV/JSON → table rows
├── services/
│   └── embedding_service.py # Azure OpenAI embedding client
├── utils/
│   ├── text_utils.py        # Text preprocessing (tokenize, lemmatize)
│   └── markdown_utils.py    # Markdown parsing helpers
└── tests/                   # Unit tests
```

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---|---|---|
| Embedding model | `text-embedding-3-small` | Azure OpenAI deployment |
| Embedding dimensions | 1536 | Vector size |
| Chunk size | 300–500 tokens | Min/max tokens per chunk |
| Context window | ±1 chunk | Surrounding chunks for generation context |
| Categories | domain, policies, runbooks | Document folder → category mapping |

## Testing

```bash
# Run all tests
make test

# With coverage
make test-cov
```
