# Requirements Management

## Overview

RAE Memory API requirements are split into multiple files for Docker image optimization and flexible deployment.

## Files

### `requirements-base.txt` (Recommended)
**Lightweight API dependencies (~500MB)**

Contains only essential dependencies:
- FastAPI & Uvicorn
- Database clients (asyncpg, qdrant-client)
- LLM API clients (OpenAI, Anthropic, Google)
- Observability tools
- Background tasks (Celery, Redis)

**Use when:**
- Running in production with external API services
- Docker image size is a concern
- Using dedicated microservices for ML workloads

### `requirements-ml.txt` (Optional)
**Heavy ML dependencies (~3-4GB)**

Contains large ML libraries:
- `sentence-transformers` - Local embeddings
- `spacy` + models - NLP & entity recognition
- `presidio` - PII detection
- `onnxruntime` - Model inference optimization

**Use when:**
- Need local embeddings (no external API)
- Running PII detection locally
- Air-gapped or offline environments

⚠️ **Warning**: Including ML dependencies increases Docker image from ~500MB to 3-5GB

### `requirements-test.txt`
**Testing dependencies**

Contains pytest, coverage, and testing utilities.

### `requirements.txt` (Main)
**Master file with references**

References other files and provides installation instructions.

## Installation

### Production (Lightweight)
```bash
pip install -r requirements-base.txt
```

### Production (Full ML)
```bash
pip install -r requirements-base.txt -r requirements-ml.txt
```

### Development
```bash
pip install -r requirements-base.txt -r requirements-test.txt
```

## Docker Optimization

### Before Optimization
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt  # 3-5GB image!
```

### After Optimization
```dockerfile
FROM python:3.11-slim
COPY requirements-base.txt .
RUN pip install -r requirements-base.txt  # 500MB image!

# Optional: Add ML dependencies only if needed
# COPY requirements-ml.txt .
# RUN pip install -r requirements-ml.txt
```

## Architecture Recommendations

### Recommended: Microservices
```
┌─────────────────────┐
│   memory-api        │  ← Lightweight (requirements-base.txt)
│   (FastAPI)         │     Uses external APIs
└─────────────────────┘
          │
          ├──→ OpenAI API (embeddings)
          ├──→ Anthropic API (LLM)
          └──→ reranker-service (local ML)
                   └─ (requirements-ml.txt)
```

### Alternative: Monolith
```
┌─────────────────────┐
│   memory-api        │  ← Heavy (requirements-base + ml)
│   (All-in-one)      │     ~3-5GB Docker image
└─────────────────────┘
```

## Migration Guide

If you have existing code using local ML libraries:

### 1. Move Embeddings to External API
```python
# Before (Heavy)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode(text)

# After (Lightweight)
import openai
response = openai.embeddings.create(
    model="text-embedding-3-small",
    input=text
)
embedding = response.data[0].embedding
```

### 2. Move PII Detection to Dedicated Service
```python
# Before (Heavy)
from presidio_analyzer import AnalyzerEngine
analyzer = AnalyzerEngine()
results = analyzer.analyze(text=text, language='en')

# After (Lightweight)
import httpx
response = httpx.post(
    "http://pii-service:8001/analyze",
    json={"text": text}
)
results = response.json()
```

### 3. Use Celery for Heavy Tasks
```python
# Schedule heavy ML task in background worker
from apps.memory_api.tasks import extract_graph_lazy

# Non-blocking, uses cheaper model
extract_graph_lazy.delay(
    memory_ids=[...],
    tenant_id=tenant_id,
    use_mini_model=True  # gpt-4o-mini instead of gpt-4
)
```

## Cost Analysis

### API-Based (Lightweight)
- **Docker Image**: 500MB
- **Memory Usage**: 200-500MB
- **Startup Time**: 2-3s
- **Cost**: $0.0001/1K tokens (OpenAI)

### Local ML (Heavy)
- **Docker Image**: 3-5GB
- **Memory Usage**: 2-4GB
- **Startup Time**: 30-60s
- **Cost**: Infrastructure ($$$)

## Best Practices

1. **Use `requirements-base.txt` by default**
2. **Add ML dependencies only when necessary**
3. **Consider dedicated microservices for ML workloads**
4. **Use external APIs when available (OpenAI, HuggingFace)**
5. **Lazy-load ML models in background tasks**
6. **Monitor Docker image sizes**

## See Also

- [apps/reranker-service](../reranker-service/) - Dedicated ML service
- [Docker Optimization Guide](../../docs/guides/production-deployment.md)
- [Phase 2 Features](../../docs/guides/phase2-features.md)
