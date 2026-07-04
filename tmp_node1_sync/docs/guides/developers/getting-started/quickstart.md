# Quick Start Guide

Get RAE up and running in less than 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10 or higher
- (Optional) LLM API key (OpenAI, Anthropic, or Gemini)

## Step 1: Clone the Repository

```bash
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory
cd RAE-agentic-memory
```

## Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your LLM API keys (optional for getting started)
nano .env
```

**Minimal configuration:**
```env
# LLM Provider (optional - defaults to mock for testing)
LLM_PROVIDER=openai  # or anthropic, gemini, ollama
OPENAI_API_KEY=your-key-here

# Database
DATABASE_URL=postgresql://rae:rae@postgres:5432/rae

# Redis
REDIS_URL=redis://redis:6379/0

# Vector Store
RAE_VECTOR_BACKEND=qdrant
QDRANT_URL=http://qdrant:6333
```

## Step 3: Start Services

### Option A: Using Docker Compose (Recommended)

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f rae-api
```

### Option B: Using Makefile

```bash
# Start everything
make start

# This will:
# - Start infrastructure (Postgres, Redis, Qdrant)
# - Initialize database
# - Start API server
# - Start dashboard (optional)
```

## Step 4: Verify Installation

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "vector_store": "healthy",
  "version": "1.0.0"
}
```

### Interactive API Documentation

Open your browser and navigate to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Step 5: Store Your First Memory

### Using curl

```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: quickstart-demo" \
  -H "X-Project-ID: my-first-project" \
  -d '{
    "layer": "episodic",
    "content": "User prefers dark mode in all applications",
    "tags": ["preference", "ui"]
  }'
```

### Using Python SDK

```bash
# Install SDK
pip install rae-memory-sdk

# Or install from local source
cd sdk/python/rae_memory_sdk
pip install -e .
```

```python
import asyncio
from rae_memory_sdk import MemoryClient

async def main():
    # Initialize client
    client = MemoryClient(
        api_url="http://localhost:8000",
        tenant_id="quickstart-demo",
        project_id="my-first-project"
    )

    # Store a memory
    response = await client.store_memory(
        content="User prefers dark mode in all applications",
        layer="episodic",
        tags=["preference", "ui"]
    )

    print(f"Stored memory: {response['id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 6: Query Memories

### Semantic Search

```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: quickstart-demo" \
  -H "X-Project-ID: my-first-project" \
  -d '{
    "query": "What are the user UI preferences?",
    "top_k": 5
  }'
```

### Using Python SDK

```python
# Query memories
results = await client.query_memory(
    query="What are the user UI preferences?",
    top_k=5
)

for result in results:
    print(f"[Score: {result['score']:.3f}] {result['content']}")
```

## Step 7: Run Interactive Tutorial

We've prepared an interactive tutorial that walks you through all RAE features:

```bash
python examples/quickstart.py
```

This will demonstrate:
- ✅ Storing memories in different layers
- ✅ Semantic search
- ✅ Knowledge graph creation
- ✅ Reflection generation
- ✅ Best practices

## Optional: Launch Dashboard

RAE includes a Streamlit dashboard for visual exploration:

```bash
# If not already running
docker compose up -d rae-dashboard

# Or run locally
cd tools/memory-dashboard
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## What's Next?

Now that RAE is running, explore:

1. **[Core Concepts](../concepts/memory-layers.md)** - Understanding memory layers
2. **[API Reference](../api/rest-api.md)** - Complete API documentation
3. **[IDE Integration](../guides/ide-integration.md)** - Connect RAE to Cursor/VSCode
4. **[Examples](../examples/)** - Real-world use cases
5. **[Production Deployment](../guides/production-deployment.md)** - Deploy to production

## Troubleshooting

### Services Not Starting

```bash
# Check Docker is running
docker --version

# Check container logs
docker compose logs

# Restart services
docker compose down
docker compose up -d
```

### Database Connection Error

```bash
# Verify Postgres is running
docker compose ps postgres

# Check database connectivity
docker compose exec postgres psql -U rae -d rae -c "SELECT 1;"

# Reinitialize database
make db-reset
```

### Vector Store Not Responding

```bash
# Check Qdrant status
curl http://localhost:6333/

# Restart Qdrant
docker compose restart qdrant
```

### API Key Issues

Make sure your `.env` file has the correct format (without quotes):
```env
# Correct
OPENAI_API_KEY=sk-...

# Incorrect - don't use quotes!
OPENAI_API_KEY="sk-..."
```

**Note:** In `.env` files, values should NOT be wrapped in quotes. Most environment file parsers handle values without quotes correctly.

## Need Help?

- 📖 [Full Documentation](../)
- 💬 [Discord Community](https://discord.gg/rae)
- 🐛 [Report Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)
- 📧 [Contact Support](mailto:lesniowskig@gmail.com)

---

**Next:** [Understanding Memory Layers →](../concepts/memory-layers.md)
