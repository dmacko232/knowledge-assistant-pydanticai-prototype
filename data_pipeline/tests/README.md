# Data Pipeline Tests

Comprehensive unit tests for the data pipeline components.

## Test Coverage

### Database Layer
- **test_relational_store.py**: Tests for RelationalStore (KPI and Employee data)
  - Connection and table creation
  - CRUD operations for KPIs and Employees
  - Querying and filtering
  - Statistics aggregation
  - Upsert functionality

- **test_vector_store.py**: Tests for VectorStore (Document chunks with embeddings)
  - Connection and table creation
  - Chunk insertion with embeddings and FTS5 content
  - Vector similarity search
  - BM25 full-text search
  - Category filtering
  - Statistics aggregation

### Processors
- **test_structured_processor.py**: Tests for StructuredDataProcessor
  - CSV processing for KPI catalog
  - JSON processing for employee directory
  - Data validation
  - Whitespace handling
  - Error handling

- **test_document_processor.py**: Tests for DocumentProcessor
  - Markdown document parsing
  - Chunking strategy
  - Metadata extraction
  - Generation chunk creation with context
  - FTS5 content generation
  - Chunk ID uniqueness

### Services
- **test_embedding_service.py**: Tests for EmbeddingService
  - Single text embedding
  - Batch embedding
  - Batch size handling
  - Mock service implementation

## Running Tests

### Install Dependencies
```bash
pip install -e ".[dev]"
```

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_relational_store.py
```

### Run Tests with Coverage
```bash
pytest --cov=. --cov-report=html
```

### Run Tests Matching Pattern
```bash
pytest -k "test_insert"
```

## Test Structure

Tests use pytest fixtures for:
- `temp_db_path`: Temporary database paths
- `temp_dir`: Temporary directories for test files
- `store`: Pre-configured database store instances
- `processor`: Pre-configured processor instances

## Key Testing Patterns

1. **Isolation**: Each test uses temporary databases and files
2. **Type Safety**: Tests verify SQLModel types are used correctly
3. **Error Handling**: Tests cover both success and error cases
4. **Edge Cases**: Tests include boundary conditions and edge cases
5. **Mock Services**: Mock implementations for external dependencies

## Architecture Improvements

The refactored codebase includes:
- **SQLModel**: Type-safe database models instead of dicts
- **Protocols**: Interface definitions for database stores
- **Embedding Service**: Abstracted embedding generation with interface
- **Proper Types**: All functions use proper type hints instead of `Dict` and `List`