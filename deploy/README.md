# Deployment Guide

## Prerequisites

- Docker & Docker Compose
- kubectl (for Kubernetes)
- kubectl context configured for target cluster

## Local Development

```bash
# Set environment variables
export DEEPSEEK_API_KEY=your_key
export LANGSMITH_API_KEY=your_key

# Start all services
docker compose up

# Start with PostgreSQL for state persistence
docker compose -f docker-compose.yml up postgres
```

## Production Deployment

### Docker Compose

```bash
# Set required environment variables
export DEEPSEEK_API_KEY=your_key
export LANGSMITH_API_KEY=your_key
export LANGSMITH_PROJECT=multiagent-prod
export POSTGRES_PASSWORD=secure_password

# Build and start production services
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
# Edit secrets.yaml with actual values
vim deploy/k8s/secrets.yaml

# Deploy
chmod +x deploy/scripts/deploy.sh
./deploy/scripts/deploy.sh

# Verify
kubectl get pods -n multiagent
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DEEPSEEK_API_KEY | Yes | DeepSeek API key for LLM |
| LANGSMITH_API_KEY | No | LangSmith key for observability |
| LANGSMITH_PROJECT | No | LangSmith project name (default: multiagent-dev) |
| POSTGRES_PASSWORD | Yes | PostgreSQL password for production |
