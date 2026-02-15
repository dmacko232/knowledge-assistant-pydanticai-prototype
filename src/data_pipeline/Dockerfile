# --------------------------------------------------------------------------
# Data Pipeline — Dockerfile
# Processes raw documents and structured data → SQLite database
# --------------------------------------------------------------------------
FROM python:3.11-slim AS base

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (sqlite-vec needs gcc to build its C extension)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Download NLTK data used by the chunker / preprocessor
RUN python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords'); nltk.download('wordnet')"

# Copy the rest of the source code
COPY . .

# Default: run the full pipeline
# Override with: docker run <image> process-documents  (or any other CLI command)
ENTRYPOINT ["python", "main.py"]
CMD ["process-all"]
