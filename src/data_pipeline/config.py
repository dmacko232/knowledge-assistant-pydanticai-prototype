"""Configuration for the data pipeline."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the data_pipeline directory so env vars are set before any getenv() below.
# Works whether you run from repo root (e.g. make run-pipeline) or from data_pipeline/.
_CONFIG_DIR = Path(__file__).resolve().parent
load_dotenv(_CONFIG_DIR / ".env")

# Project root directory (two levels up from src/data_pipeline/)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data paths
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DOCUMENTS_DIR = RAW_DATA_DIR / "documents"
STRUCTURED_DATA_DIR = RAW_DATA_DIR / "structured"

# Database paths (in root database/ folder)
DATABASE_DIR = PROJECT_ROOT / "database"
DB_PATH = DATABASE_DIR / "knowledge_assistant.sqlite"  # Single database for everything

# Output directory for logs and temporary files
OUTPUT_DIR = Path(__file__).parent / "output"

# Azure OpenAI configuration (used for chat/completions; also fallback for embeddings)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Embedding-specific config (override in .env if your embedding deployment uses a different endpoint/version)
# If unset, the generic AZURE_OPENAI_* values above are used.
AZURE_OPENAI_EMBEDDING_ENDPOINT = (
    os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT") or AZURE_OPENAI_ENDPOINT
)
AZURE_OPENAI_EMBEDDING_API_VERSION = (
    os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION") or AZURE_OPENAI_API_VERSION
)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
)
AZURE_OPENAI_EMBEDDING_API_KEY = os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY") or AZURE_OPENAI_API_KEY

EMBEDDING_DIMENSIONS = 1536

# Chunking configuration
MIN_CHUNK_SIZE = 300  # tokens
MAX_CHUNK_SIZE = 500  # tokens
CONTEXT_WINDOW = 1  # Number of surrounding chunks to include in generation chunk

# Document categories
DOCUMENT_CATEGORIES = ["domain", "policies", "runbooks"]

# FTS5 configuration (BM25 ranking built into SQLite FTS5)
# SQLite FTS5 will handle BM25 ranking internally using its bm25() function


def validate_config():
    """Validate configuration and check for required files."""
    # Embedding can use its own key/endpoint; at least one set must be present
    key = AZURE_OPENAI_EMBEDDING_API_KEY or AZURE_OPENAI_API_KEY
    endpoint = AZURE_OPENAI_EMBEDDING_ENDPOINT or AZURE_OPENAI_ENDPOINT
    if not key:
        raise ValueError(
            "No Azure OpenAI API key found. Set AZURE_OPENAI_API_KEY or AZURE_OPENAI_EMBEDDING_API_KEY in .env"
        )
    if not endpoint:
        raise ValueError(
            "No Azure OpenAI endpoint found. Set AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_EMBEDDING_ENDPOINT in .env"
        )

    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(f"Documents directory not found: {DOCUMENTS_DIR}")

    if not STRUCTURED_DATA_DIR.exists():
        raise FileNotFoundError(f"Structured data directory not found: {STRUCTURED_DATA_DIR}")

    # Create directories if they don't exist
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    validate_config()
    print("✓ Configuration validated successfully")
    print(f"  Documents: {DOCUMENTS_DIR}")
    print(f"  Structured data: {STRUCTURED_DATA_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
