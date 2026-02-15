# Data Pipeline Architecture

## Purpose

The data pipeline is a **batch-mode CLI tool** that ingests raw markdown documents and structured data (CSV, JSON), processes them, and writes everything into a single SQLite database. The backend then reads this database at runtime — it never writes to it.

The pipeline is run once (or whenever source data changes) via `make run-pipeline`.

---

## Project Structure

```
data_pipeline/
├── main.py                          # Click CLI — entry point
├── config.py                        # Paths, env vars, chunking params
├── processors/
│   ├── document_processor.py        # Markdown → chunks + FTS content
│   ├── embedding_processor.py       # Chunks → embedding vectors
│   └── structured_processor.py      # CSV/JSON → validated records
├── services/
│   └── embedding_service.py         # Azure OpenAI embedding client + mock
├── database/
│   ├── models.py                    # SQLModel table definitions
│   ├── interfaces.py                # Abstract store interface
│   ├── vector_store.py              # sqlite-vec + FTS5 storage
│   └── relational_store.py          # KPI + directory table storage
├── utils/
│   ├── text_utils.py                # Tokenization, stop-word removal, lemmatization
│   └── markdown_utils.py            # Heading-based markdown splitting
```

Tests live at the project root in `tests/data_pipeline/`:

```
tests/data_pipeline/
├── conftest.py                    # sys.path setup + shared fixtures
├── test_document_processor.py
├── test_embedding_service.py
├── test_vector_store.py
├── test_relational_store.py
└── test_structured_processor.py
```

---

## Pipeline Flow

```
data/raw/documents/**/*.md           data/raw/structured/
        │                                   │
        ▼                                   ▼
  ┌──────────────┐                   ┌──────────────┐
  │  Document     │                   │  Structured   │
  │  Processor    │                   │  Processor    │
  │  (chunking)   │                   │  (CSV/JSON)   │
  └──────┬───────┘                   └──────┬───────┘
         │                                  │
         ▼                                  │
  ┌──────────────┐                          │
  │  Embedding    │                          │
  │  Processor    │                          │
  │  (Azure OAI)  │                          │
  └──────┬───────┘                          │
         │                                  │
         ▼                                  ▼
  ┌──────────────┐                   ┌──────────────┐
  │  Vector Store │                   │  Relational   │
  │  (sqlite-vec) │                   │  Store        │
  └──────┬───────┘                   └──────┬───────┘
         │                                  │
         └──────────┬───────────────────────┘
                    ▼
     database/knowledge_assistant.sqlite
```

### Step 1: Document Processing (`DocumentProcessor`)

Markdown files are organized by category:

```
data/raw/documents/
├── domain/       # Business domain docs (KPI overviews, process guides)
├── policies/     # Company policies (security, compliance)
└── runbooks/     # Operational runbooks (deploys, incident response)
```

Each file is split into chunks using heading structure (H1/H2/H3). Two text variants are produced per chunk:

| Variant | Purpose | Content |
|---|---|---|
| `retrieval_chunk` | Embedding + BM25 search | Cleaned text of the chunk itself |
| `generation_chunk` | Sent to LLM for answer synthesis | Chunk text + ±1 surrounding chunks for richer context |

Chunking parameters (from `config.py`):

- **Min chunk size:** 300 tokens
- **Max chunk size:** 500 tokens
- **Context window:** ±1 chunk (for generation chunk)

### Step 2: Text Preprocessing (`utils/text_utils.py`)

For BM25 / FTS5 indexing, chunk text goes through:

1. **Tokenization** (NLTK `punkt_tab`)
2. **Stop-word removal** (NLTK English stop words)
3. **Lemmatization** (NLTK `WordNetLemmatizer`)

This produces the `content` column in the `fts_chunks` virtual table.

### Step 3: Embedding Generation (`EmbeddingProcessor`)

Each `retrieval_chunk` is embedded via the Azure OpenAI API:

- **Model:** `text-embedding-3-small` (configurable)
- **Dimensions:** 1536
- **Batching:** chunks are sent in batches to respect API rate limits

A `MockEmbeddingService` is available for local development without API keys (`--mock-embeddings` flag).

### Step 4: Vector Storage (`VectorStore`)

The `sqlite-vec` extension provides vector similarity search inside SQLite. The store creates three tables/indexes:

- `document_chunks` — full chunk metadata (text, document name, category, section, dates)
- `vec_chunks` — 1536-dimensional embedding vectors linked to chunk IDs
- `fts_chunks` — FTS5 virtual table for BM25 keyword search (Porter stemming enabled)

### Step 5: Structured Data Processing (`StructuredDataProcessor`)

Two structured data sources are parsed and validated:

| Source | Format | Table | Records |
|---|---|---|---|
| `kpi_catalog.csv` | CSV | `kpi_catalog` | ~15 KPIs with definitions, owner teams, primary sources |
| `directory.json` | JSON | `directory` | ~20 employees with name, email, team, role, timezone |

Both use upsert logic (insert or update by unique key) so re-running the pipeline is idempotent.

---

## Database Schema

Single file: `database/knowledge_assistant.sqlite`

```
┌───────────────────────┐      ┌──────────────────────┐
│  document_chunks      │      │   vec_chunks         │
│───────────────────────│      │──────────────────────│
│  chunk_id (PK, UQ)    │◀────│  chunk_id (PK)       │
│  document_name        │      │  embedding [1536]    │
│  category             │      └──────────────────────┘
│  section_header       │
│  retrieval_chunk      │      ┌──────────────────────┐
│  generation_chunk     │      │   fts_chunks (FTS5)  │
│  last_updated         │      │──────────────────────│
│  word_count           │      │  chunk_id            │
│  chunk_metadata (JSON)│◀────│  document_name       │
│  created_at           │      │  category            │
└───────────────────────┘      │  section_header      │
                               │  content (stemmed)   │
┌───────────────────────┐      └──────────────────────┘
│  kpi_catalog          │
│───────────────────────│
│  id (PK)              │      ┌──────────────────────┐
│  kpi_name (UQ)        │      │   directory          │
│  definition           │      │──────────────────────│
│  owner_team           │      │  id (PK)             │
│  primary_source       │      │  name                │
│  last_updated         │      │  email (UQ)          │
│  created_at           │      │  team                │
└───────────────────────┘      │  role                │
                               │  timezone            │
                               │  created_at          │
                               └──────────────────────┘
```

---

## CLI Commands

The pipeline is controlled via `python main.py <command>` (or `make` shortcuts):

| Command | Make target | Description |
|---|---|---|
| `process-all` | `make run-pipeline` | Full pipeline (documents + structured data) |
| `process-documents` | — | Documents only (skip structured data) |
| `process-structured` | — | Structured data only (skip documents) |
| `reset` | `make reset-db` | Drop all tables |
| `stats` | `make stats` | Show row counts per table |
| `dump-db` | — | Dump tables with sample rows |
| `search-vector <query>` | — | Test vector similarity search |
| `search-bm25 <query>` | — | Test BM25 keyword search |

The `--mock-embeddings` flag on `process-all` and `process-documents` uses random vectors instead of calling Azure OpenAI, allowing database creation without API keys.

---

## Configuration

All settings live in `data_pipeline/config.py`, loaded from `data_pipeline/.env`:

| Setting | Default | Description |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | — | API key for embedding generation |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-small` | Embedding model deployment name |
| `EMBEDDING_DIMENSIONS` | 1536 | Embedding vector dimensions |
| `MIN_CHUNK_SIZE` | 300 | Minimum chunk size in tokens |
| `MAX_CHUNK_SIZE` | 500 | Maximum chunk size in tokens |
| `CONTEXT_WINDOW` | 1 | Surrounding chunks for generation context |

---

## Testing

```bash
make test        # Run data pipeline tests
make test-cov    # With coverage report
```

| Test file | Coverage |
|---|---|
| `test_document_processor.py` | Markdown chunking, heading parsing, context windows |
| `test_embedding_service.py` | Azure client calls, mock service, batching |
| `test_vector_store.py` | Table creation, chunk insertion, search queries |
| `test_relational_store.py` | KPI/directory upsert, stats, reset |
| `test_structured_processor.py` | CSV/JSON parsing, validation |
