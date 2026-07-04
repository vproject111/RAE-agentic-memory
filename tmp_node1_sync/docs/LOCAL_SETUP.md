# RAE – Local Setup Guide (Local-First & Cloud)

This document explains how to run RAE-agentic-memory **locally on your own machine** for development, testing, and privacy-focused experiments.

It supports two modes:
1.  **Cloud Hybrid**: Using external LLM providers (OpenAI, Anthropic, Gemini) - requires API keys.
2.  **Local First**: Using local LLMs (via Ollama) - **no data leaves your machine**.

---

## 1. Prerequisites

Before you start, make sure you have:

- **Git**
- **Docker** and **Docker Compose**
- **Make** (optional, but convenient)
- A modern **Linux** or **macOS** machine (Windows via WSL2 is fine)

**For Local First Mode (Ollama):**
- At least **16 GB RAM** (32 GB recommended)
- Docker installed

**For Cloud Hybrid Mode:**
- API credentials for at least one provider (OpenAI, Anthropic, or Google).

---

## 2. Clone the repository

```bash
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory.git
cd RAE-agentic-memory
```

---

## 3. Configure environment variables

Copy the example configuration:

```bash
cp .env.example .env
```

Edit `.env` based on your chosen mode:

### Option A: Local First (Privacy Focused) 🔒

Use this mode to run RAE entirely offline or without sending data to external providers.

1.  **Install & Run Ollama**:
    Follow instructions at [ollama.com](https://ollama.com) or run via Docker.
    Ensure Ollama is running on port `11434`.

2.  **Pull a Model**:
    ```bash
    ollama run llama3  # or phi3, mistral, etc.
    ```

3.  **Edit `.env`**:
    ```ini
    # Backend Configuration
    RAE_LLM_BACKEND=ollama
    OLLAMA_API_URL=http://host.docker.internal:11434  # If running Ollama on host
    # or http://ollama:11434 if running via Docker service

    # Model Selection
    RAE_LLM_MODEL_DEFAULT=llama3

    # Security
    TENANCY_ENABLED=false
    ENABLE_API_KEY_AUTH=false
    ```

### Option B: Cloud Hybrid (Best Performance) ☁️

Use this mode for production-grade reasoning capabilities.

1.  **Edit `.env`**:
    ```ini
    # Backend Configuration
    RAE_LLM_BACKEND=openai  # or anthropic, gemini

    # API Keys (Uncomment and fill)
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-ant-...
    GEMINI_API_KEY=...
    ```

---

## 4. Run RAE locally with Docker

Start the stack using Docker Compose:

```bash
# Standard setup
docker compose up -d --build

# Or use the lite profile (lower resource usage)
docker compose -f docker compose.lite.yml up -d --build
```

### Running Ollama via Docker (Optional)

If you don't have Ollama installed on your host, add this service to your `docker compose.yml`:

```yaml
  ollama:
    image: ollama/ollama
    container_name: rae-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
```

Then run:
```bash
docker compose up -d
docker exec -it rae-ollama ollama run llama3
```

---

## 5. Verify installation

1.  **API Health Check**:
    ```bash
    curl http://localhost:8000/health
    ```
    Expected: `{"status": "ok", ...}`

2.  **Open API Documentation**:
    Navigate to [http://localhost:8000/docs](http://localhost:8000/docs).

3.  **Dashboard**:
    Navigate to [http://localhost:8501](http://localhost:8501).

---

## 6. First memory write (Smoke Test)

Using `curl`:

```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: demo-tenant" \
  -d '{
    "content": "RAE is running locally and securely.",
    "layer": "episodic",
    "tags": ["test", "local-first"]
  }'
```

If using **Local First** mode, check your Ollama logs to see the inference happening locally!

---

## 7. Stopping and cleaning up

To stop the stack:
```bash
docker compose down
```

To remove all data (database, vectors, logs):
```bash
docker compose down -v
```

---

## 8. Troubleshooting

- **"Connection refused" to Ollama**:
  - If RAE is in Docker and Ollama is on Host: use `OLLAMA_API_URL=http://host.docker.internal:11434`.
  - Linux users might need `OLLAMA_API_URL=http://172.17.0.1:11434`.

- **High RAM Usage**:
  - Local LLMs are memory intensive. Switch to "Cloud Hybrid" or use quantized models (e.g., `llama3:8b-q4_0`).

- **Database errors**:
  - Run `./scripts/init-database.sh` to manually re-initialize the schema if automatic migration failed.

