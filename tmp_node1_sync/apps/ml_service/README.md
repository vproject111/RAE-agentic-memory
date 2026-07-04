# RAE ML Service

**Machine Learning Microservice for RAE** - Handles computationally expensive ML operations separate from the main API.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-red)

## Overview

The ML Service is a dedicated microservice that offloads heavy machine learning operations from the main RAE Memory API. This architectural separation ensures:

- **Performance**: Main API remains fast and responsive
- **Scalability**: ML operations can be scaled independently
- **Resource isolation**: Memory-intensive models don't impact API performance
- **Maintainability**: Clear separation of concerns

## Features

### Core Capabilities

- **Local Embeddings** - Fast embedding generation using SentenceTransformers
- **Entity Resolution** - Clustering and merging similar entities
- **Keyword Extraction** - NLP-based keyword extraction with spaCy
- **Triple Extraction** - Knowledge graph triple extraction (subject-predicate-object)
- **NLP Processing** - Named entity recognition, POS tagging, dependency parsing

### Benefits

- No external API dependencies for embeddings
- High throughput - handle hundreds of requests/second
- Cost-effective - no per-token charges
- Privacy-preserving - all processing happens locally
- Flexible - easy to add new ML models

## Architecture

```
┌─────────────────┐
│   RAE Memory    │
│      API        │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│   ML Service    │
│   (Port 8001)   │
├─────────────────┤
│ • Embeddings    │
│ • Entity Res.   │
│ • NLP Tasks     │
│ • Triples       │
└─────────────────┘
```

**Communication:** REST API (JSON)
**Port:** 8001
**Health Check:** `/health`

## API Endpoints

### 1. Generate Embeddings

Generate vector embeddings for text using local models.

**Endpoint:** `POST /embeddings`

**Request:**
```json
{
  "texts": ["Hello world", "AI is awesome"],
  "model": "all-MiniLM-L6-v2"
}
```

**Response:**
```json
{
  "embeddings": [[0.123, -0.456, ...], [0.789, 0.234, ...]],
  "model": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

**Supported Models:**
- `all-MiniLM-L6-v2` (384 dims) - Fast, lightweight
- `all-mpnet-base-v2` (768 dims) - Higher quality
- `paraphrase-multilingual-MiniLM-L12-v2` (384 dims) - Multilingual

**Example (curl):**
```bash
curl -X POST http://localhost:8001/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello world"],
    "model": "all-MiniLM-L6-v2"
  }'
```

**Example (Python):**
```python
import requests

response = requests.post(
    "http://localhost:8001/embeddings",
    json={
        "texts": ["Hello world", "Machine learning is fun"],
        "model": "all-MiniLM-L6-v2"
    }
)

embeddings = response.json()["embeddings"]
print(f"Generated {len(embeddings)} embeddings")
```

---

### 2. Resolve Entities

Cluster and merge similar entities in a knowledge graph.

**Endpoint:** `POST /resolve-entities`

**Request:**
```json
{
  "nodes": [
    {"name": "New York", "type": "location"},
    {"name": "NYC", "type": "location"},
    {"name": "John Smith", "type": "person"}
  ],
  "similarity_threshold": 0.85
}
```

**Response:**
```json
{
  "merge_groups": [["New York", "NYC"]],
  "statistics": {
    "total_nodes": 3,
    "clusters": 2,
    "merges": 1
  }
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8001/resolve-entities \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [
      {"name": "AI", "type": "concept"},
      {"name": "Artificial Intelligence", "type": "concept"}
    ],
    "similarity_threshold": 0.85
  }'
```

---

### 3. Extract Keywords

Extract important keywords from text using NLP.

**Endpoint:** `POST /extract-keywords`

**Request:**
```json
{
  "text": "Machine learning is transforming industries...",
  "max_keywords": 10,
  "language": "en"
}
```

**Response:**
```json
{
  "keywords": [
    {"text": "machine learning", "score": 0.95, "pos": "NOUN"},
    {"text": "transform", "score": 0.87, "pos": "VERB"}
  ]
}
```

**Example (Python):**
```python
response = requests.post(
    "http://localhost:8001/extract-keywords",
    json={
        "text": "Artificial intelligence is revolutionizing healthcare.",
        "max_keywords": 5,
        "language": "en"
    }
)

keywords = response.json()["keywords"]
for kw in keywords:
    print(f"{kw['text']}: {kw['score']:.2f}")
```

---

### 4. Extract Triples

Extract knowledge graph triples (subject-predicate-object) from text.

**Endpoint:** `POST /extract-triples`

**Request:**
```json
{
  "text": "John works at Google in California.",
  "language": "en",
  "method": "dependency"
}
```

**Response:**
```json
{
  "triples": [
    {
      "subject": "John",
      "predicate": "works_at",
      "object": "Google",
      "confidence": 0.92
    },
    {
      "subject": "Google",
      "predicate": "located_in",
      "object": "California",
      "confidence": 0.88
    }
  ]
}
```

**Methods:**
- `dependency` - Uses spaCy dependency parsing (more accurate)
- `simple` - Simple pattern matching (faster)

**Example (curl):**
```bash
curl -X POST http://localhost:8001/extract-triples \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Einstein developed the theory of relativity.",
    "method": "dependency"
  }'
```

---

### 5. Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "ml-service"
}
```

---

### 6. Service Info

**Endpoint:** `GET /`

**Response:**
```json
{
  "service": "RAE ML Service",
  "version": "2.0.0",
  "status": "operational",
  "endpoints": {
    "health": "/health",
    "embeddings": "/embeddings",
    "resolve_entities": "/resolve-entities",
    "extract_keywords": "/extract-keywords",
    "extract_triples": "/extract-triples"
  },
  "features": [
    "Local embedding generation (SentenceTransformers)",
    "Entity resolution and clustering",
    "Keyword extraction (spaCy)",
    "Knowledge triple extraction",
    "NLP processing"
  ]
}
```

## Installation

### Standalone Deployment

```bash
cd apps/ml_service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Docker Deployment

```bash
# Build image
docker build -t rae-ml-service .

# Run container
docker run -p 8001:8001 rae-ml-service
```

### With Docker Compose

ML Service is included in the main `docker compose.yml`:

```bash
# From project root
docker compose up -d ml-service
```

## Configuration

### Environment Variables

Currently, the ML Service doesn't require configuration. Models are loaded automatically on first use.

**Optional (future):**
- `ML_SERVICE_PORT` - Port to listen on (default: 8001)
- `EMBEDDING_MODEL` - Default embedding model
- `SPACY_MODEL` - spaCy model to use (default: en_core_web_sm)

### Model Management

Models are downloaded automatically on first request:
- **SentenceTransformers**: `~/.cache/torch/sentence_transformers/`
- **spaCy**: `~/.cache/spacy/`

To pre-download models:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
python -m spacy download en_core_web_sm
```

## Development

### Project Structure

```
apps/ml_service/
├── main.py                    # FastAPI app and endpoints
├── services/
│   ├── __init__.py
│   ├── embedding_service.py   # Embedding generation
│   ├── entity_resolution.py   # Entity clustering
│   ├── nlp_service.py         # Keyword extraction
│   └── triple_extraction.py   # Triple extraction
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_api_integration.py
│   ├── test_embedding_service.py
│   ├── test_entity_resolution_service.py
│   ├── test_nlp_service.py
│   └── test_triple_extraction_service.py
├── Dockerfile
└── requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_embedding_service.py

# Run with coverage
pytest --cov=. --cov-report=html tests/

# Run integration tests
pytest tests/test_api_integration.py -v
```

**Test Coverage:**
- 6 test files
- 43+ test functions
- 1308 lines of test code

### Adding New ML Models

To add a new ML capability:

1. Create a new service in `services/`:
   ```python
   # services/my_service.py
   class MyMLService:
       def process(self, input_data):
           # Your ML logic here
           return results
   ```

2. Add endpoint in `main.py`:
   ```python
   @app.post("/my-endpoint")
   async def my_endpoint(req: MyRequest):
       service = MyMLService()
       results = service.process(req.data)
       return {"results": results}
   ```

3. Add tests in `tests/test_my_service.py`

4. Update this README with documentation

## Performance

### Benchmarks

Tested on: Intel i7-10700K, 32GB RAM

| Operation | Throughput | Latency (p50) | Latency (p99) |
|-----------|------------|---------------|---------------|
| Embeddings (1 text) | 500 req/s | 2ms | 15ms |
| Embeddings (10 texts) | 100 req/s | 10ms | 50ms |
| Entity Resolution | 50 req/s | 20ms | 100ms |
| Keyword Extraction | 200 req/s | 5ms | 25ms |
| Triple Extraction | 80 req/s | 12ms | 60ms |

### Optimization Tips

1. **Batch requests**: Send multiple texts in one request
2. **Pre-warm models**: Hit endpoints on startup
3. **Scale horizontally**: Run multiple ML service instances
4. **Use faster models**: Trade accuracy for speed if needed
5. **Cache results**: Cache embeddings for common texts

## Troubleshooting

### Models not downloading

```bash
# Manually download models
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
python -m spacy download en_core_web_sm
```

### Out of memory errors

```bash
# Reduce batch size or use smaller models
# For embeddings, use 'all-MiniLM-L6-v2' instead of 'all-mpnet-base-v2'
```

### Slow first request

Models are loaded lazily on first use. Pre-warm by hitting endpoints after startup:

```bash
curl http://localhost:8001/health
curl -X POST http://localhost:8001/embeddings -d '{"texts":["warmup"]}'
```

## API Documentation

### Interactive Docs

Once the service is running, visit:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

These provide interactive API exploration and testing.

## Integration with RAE

The ML Service is automatically integrated when using Docker Compose:

```yaml
# In main docker compose.yml
ml-service:
  build: ./apps/ml_service
  ports:
    - "8001:8001"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
```

RAE Memory API connects via:
```python
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8001")
```

## License

Part of the RAE (Reflective Agentic Memory Engine) project.

## Contributing

1. Write tests for new features
2. Maintain >80% test coverage
3. Update this README with new endpoints
4. Follow existing code patterns

## Support

- Documentation: `docs/`
- Issues: GitHub Issues
- Tests: `pytest tests/ -v`
