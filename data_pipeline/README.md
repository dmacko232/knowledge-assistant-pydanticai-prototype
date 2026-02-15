# Data Pipeline

This data pipeline processes markdown documents and structured data (KPIs, employee directory) for the Northwind Commerce knowledge assistant.

## Features

- **Document Processing**: Chunks markdown files by structure, generates embeddings, stores in vector database
- **Structured Data**: Parses CSV/JSON files and stores in relational database
- **Vector Search**: Semantic search using OpenAI embeddings
- **BM25 Search**: Keyword-based search using SQLite FTS5
- **CLI**: Simple command-line interface for running the pipeline

## Setup

### 1. Install Dependencies

```bash
cd data_pipeline
pip install -e .
```

### 2. Configure API Key

Create a `.env` file with your OpenAI API key:

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Download NLTK Data

NLTK data will be downloaded automatically on first run.

## Usage

### Run Full Pipeline

Process all documents and structured data:

```bash
python main.py process-all
```

This will:
1. Process all markdown documents in `data/raw/documents/`
2. Chunk documents by structure (300-500 tokens per chunk)
3. Generate embeddings using OpenAI text-embedding-3-small
4. Store chunks in vector database with FTS5 index
5. Process KPI catalog and employee directory
6. Store structured data in relational database

### Process Only Documents

```bash
python main.py process-documents
```

### Process Only Structured Data

```bash
python main.py process-structured
```

### View Statistics

```bash
python main.py stats
```

### Search Documents

**Vector search** (semantic):
```bash
python main.py search-vector "KPI definitions" --limit 5
```

**BM25 search** (keyword):
```bash
python main.py search-bm25 "security policy" --limit 5 --category policies
```

### Reset Databases

```bash
python main.py reset
```

## Output

The pipeline creates two SQLite databases in `data_pipeline/output/`:

- **vector_db.sqlite**: Document chunks with embeddings and FTS5 index
- **relational_db.sqlite**: KPI catalog and employee directory

## Database Schema

### Vector Store (vector_db.sqlite)

**document_chunks**: Main chunks table with metadata
- chunk_id, document_name, category, section_header
- retrieval_chunk, generation_chunk
- last_updated, word_count, metadata

**vec_chunks**: Vector embeddings (using sqlite-vec)
- chunk_id, embedding (1536 dimensions)

**fts_chunks**: Full-text search index (using FTS5)
- chunk_id, document_name, category, section_header, content

### Relational Store (relational_db.sqlite)

**kpi_catalog**: KPI definitions
- kpi_name, definition, owner_team, primary_source, last_updated

**directory**: Employee directory
- name, email, team, role, timezone

## Architecture

```
data_pipeline/
├── main.py              # CLI entry point
├── config.py            # Configuration
├── database/
│   ├── vector_store.py  # Vector DB with sqlite-vec + FTS5
│   └── relational_store.py  # Relational tables
├── processors/
│   ├── document_processor.py    # Markdown chunking
│   ├── embedding_processor.py   # OpenAI embeddings
│   └── structured_processor.py  # CSV/JSON parsing
└── utils/
    ├── text_utils.py        # Text preprocessing
    └── markdown_utils.py    # Markdown parsing
```

## Configuration

Edit `config.py` to customize:
- Embedding model (default: text-embedding-3-small)
- Chunk size (default: 300-500 tokens)
- Context window (default: ±1 chunk)
- Document categories

## Cost Estimation

Embedding ~20 documents with ~100 chunks:
- Tokens: ~50,000
- Cost: ~$0.001 (OpenAI text-embedding-3-small @ $0.02/1M tokens)

## Notes

- **BM25 in SQLite**: Uses FTS5 for BM25 ranking (no external library needed)
- **Vector Search**: Brute-force search (no ANN index) - fast enough for small datasets
- **Chunking Strategy**: Chunks by markdown structure (headers) for semantic coherence
- **Generation Chunks**: Include surrounding context for better LLM generation

## Troubleshooting

**Import errors**: Make sure you're in the `data_pipeline` directory when running commands

**API key error**: Create `.env` file with valid `OPENAI_API_KEY`

**NLTK data**: Will download automatically on first run (punkt, stopwords, wordnet)
