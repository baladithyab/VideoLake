FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (minimal; tests/benchmarks only)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (reuse main project requirements if present)
COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copy just what we need for benchmarking
COPY scripts/ ./scripts/
COPY src/ ./src/
COPY embeddings/ ./embeddings/

ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/benchmark_backend.py", "--help"]

