FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ ./core/
COPY agents/ ./agents/
COPY pipelines/ ./pipelines/
COPY prompts/ ./prompts/
COPY mcp/ ./mcp/
COPY services/ ./services/
COPY skills/ ./skills/

ENV PYTHONPATH=/app

# Development entrypoint
CMD ["python", "-m", "pipelines.collaboration_pipeline"]
