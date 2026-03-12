# Multi-stage build for efficient benchmark runner
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Final stage - minimal runtime image
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy benchmark scripts and dependencies
RUN mkdir -p /app/scripts /app/embeddings/cc-open-samples-marengo /app/src
COPY scripts/benchmark_backend.py /app/scripts/
COPY scripts/backend_adapters.py /app/scripts/
COPY src/ /app/src/
COPY embeddings/cc-open-samples-marengo/ /app/embeddings/cc-open-samples-marengo/

# Copy entrypoint script
COPY docker/benchmark-runner/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=us-east-1
ENV PYTHONPATH=/app

# Create output directory
RUN mkdir -p /app/results

# Run as non-root user for security
RUN useradd -m -u 1000 benchmark && \
    chown -R benchmark:benchmark /app
USER benchmark

ENTRYPOINT ["/app/entrypoint.sh"]

