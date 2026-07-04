# RAE — Reflective Agentic-memory Engine
## Executive Summary

RAE is an open-source memory engine designed to solve one of the core limitations of modern AI agents:
**persistent, structured, auditable long-term memory with cost-aware reasoning**.

Unlike classical RAG systems or single-layer vector memories, RAE introduces a **4-layer memory architecture**, a **graph-based semantic model**, and a **reflection engine** that maintains coherence, relevance, and stability of knowledge over time.

## Target Audience

RAE is designed for:

- **researchers** studying long-term memory in AI,
- **enterprises** that need auditability and governance (ISO 42001),
- **developers** building agent systems that must retain context across sessions,
- **public institutions** requiring transparency and traceability.

## Key Features

- **4-Layer Memory Stack** (episodic, semantic, graph, reflective)
- **GraphRAG + Embeddings Hybrid Retrieval**
- **Reflection Engine V2** (summarization, pruning, reinforcement)
- **Full ISO 42001 Governance Layer** with tests
- **OpenTelemetry instrumentation** for scientific analysis
- **A/B Testing and Benchmarking Framework**
- **Multi-tenant architecture** (Postgres + Qdrant)
- **Local-first, reproducible, open-source design**

## Why RAE Matters

AI companies (including AWS, Google, Meta) publicly recognize the memory bottleneck as the *main* obstacle for reliable agentic systems.

RAE provides:
- a **practical solution**,
- an **academically interesting architecture**,
- a **fully open platform** for experimentation.

## Architecture Overview

### Memory Layers

1. **Episodic Memory** – Short-term contextual traces
   - Captures recent interactions
   - Fast access, limited capacity
   - Automatic consolidation to upper layers

2. **Semantic Memory** – Vector embeddings with hybrid retrieval
   - Dense vector representations
   - Similarity-based search
   - Integration with reranking

3. **Knowledge Graph Memory** – Entity and relation extraction
   - Structured knowledge representation
   - Graph traversal and reasoning
   - Community detection and clustering

4. **Reflective Memory** – Long-term consolidation
   - Pattern recognition across memories
   - Importance-based pruning
   - Strategic memory reinforcement

### Reflection Engine

The reflection process operates as a **Markov Decision Process** that:
- Optimizes memory quality under cost constraints
- Balances exploration vs exploitation
- Maintains knowledge stability over time
- Adapts to changing contexts

## Enterprise-Grade Features

### ISO 42001 Compliance

- **Risk assessment** for AI operations
- **Provenance tracking** for all memories
- **Human oversight** (HITL) for critical decisions
- **Circuit breakers** for safety constraints
- **Audit logs** for all operations

### Multi-Tenancy

- Isolated memory spaces per tenant
- Project-level segmentation
- Role-based access control (RBAC)
- Data retention policies

### Observability

- **OpenTelemetry** instrumentation
- Distributed tracing
- Custom metrics and dashboards
- Performance profiling

## Use Cases

### Research & Academia

- Long-term memory experiments
- Agent behavior analysis
- Benchmarking memory systems
- Reproducible research

### Enterprise Applications

- Intelligent assistants with persistent memory
- Internal knowledge automation
- Production/operations decision support
- Customer service with context retention

### Regulated Industries

- Explainable AI for compliance
- Auditable decision trails
- Privacy-preserving memory (PII scrubbing)
- Cost-controlled LLM operations

## Technical Stack

- **Python 3.11+**
- **PostgreSQL** with pgvector extension
- **Qdrant** vector database
- **Redis** for caching
- **FastAPI** for REST API
- **Celery** for async tasks
- **Docker Compose** for deployment

## Deployment Options

### RAE Lite
- Minimal resource usage
- 4 CPU cores, 8GB RAM
- Perfect for laptops and testing
- 5-10GB disk space

### RAE Standard
- Recommended for research
- 8-16 CPU cores, 16-32GB RAM
- Full feature set
- 20-50GB disk space

### RAE Enterprise
- Production-ready
- Kubernetes deployment
- High availability
- Horizontal scaling

## Call for Collaboration

We invite researchers, students, and AI labs to:
- **test the system**,
- **evaluate retrieval quality**,
- **compare with baseline RAG methods**,
- **participate in joint research or publications**.

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/dreamsoft-pro/RAE-agentic-memory
   ```

2. Start RAE Lite:
   ```bash
   docker compose -f docker-compose.lite.yml up -d
   ```

3. Run tests:
   ```bash
   make test-unit
   ```

4. See full documentation:
   - [Testing Kit](../testing/RAE_TESTING_KIT.md)
   - [Benchmark Starter](../testing/BENCHMARK_STARTER.md)
   - [Research Invitation](RESEARCH_INVITATION_LETTER.md)

## Contact

**Grzegorz Leśniowski**
Independent Researcher

- GitHub: https://github.com/dreamsoft-pro/RAE-agentic-memory
- Issues: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues

---

**RAE is open-source, free to use, and ready for academic and commercial applications.**
