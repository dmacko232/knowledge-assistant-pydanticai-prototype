# --------------------------------------------------------------------------
# Backend — Dockerfile
# FastAPI + PydanticAI agent serving grounded Q&A
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

# Copy the rest of the source code
COPY . .

# FastAPI listens on port 8000
EXPOSE 8000

# Run uvicorn — production mode (no --reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
