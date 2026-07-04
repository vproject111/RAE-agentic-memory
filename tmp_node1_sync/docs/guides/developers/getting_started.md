# Getting Started with RAE

This guide will walk you through the process of setting up a local instance of the RAE Agentic Memory Engine, from the infrastructure to the API, and show you how to perform your first memory operations.

## Prerequisites

Before you begin, make sure you have the following installed:

-   **Python**: Version 3.10 or higher.
-   **Docker and Docker Compose**: For running the infrastructure services.
-   **(Optional) LLM API Keys**: If you want to use a hosted LLM like Gemini or OpenAI, you will need to have the appropriate API keys.

## 1. Setup the Infrastructure

RAE's core infrastructure (PostgreSQL, Qdrant, Redis) is managed using Docker Compose.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/dreamsoft-pro/RAE-agentic-memory.git
    cd RAE-agentic-memory
    ```

2.  **Start the services**:
    ```bash
    cd infra
    docker compose up -d
    cd ..
    ```

3.  **Verify the containers are running**:
    You can check the status of the containers with `docker ps`:
    ```bash
    docker ps
    ```
    You should see output similar to this:
    ```
    CONTAINER ID   IMAGE                  COMMAND                  CREATED         STATUS         PORTS                                       NAMES
    ...            qdrant/qdrant:latest   "./entrypoint.sh"        5 seconds ago   Up 4 seconds   0.0.0.0:6333-6334->6333-6334/tcp             rae-qdrant
    ...            redis:7-alpine         "docker-entrypoint.s…"   5 seconds ago   Up 4 seconds   0.0.0.0:6379->6379/tcp                      rae-redis
    ...            postgres:16-alpine     "docker-entrypoint.s…"   5 seconds ago   Up 4 seconds   0.0.0.0:5432->5432/tcp                      rae-postgres
    ```

## 2. Configure the Environment

The RAE Memory API is configured using environment variables.

1.  **Copy the example environment file**:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file**:
    Open the `.env` file and configure it for your setup. The most important variables are:
    -   `DATABASE_URL`: The connection string for the PostgreSQL database. The default should work with the Docker Compose setup.
    -   `RAE_VECTOR_BACKEND`: The vector store to use. Can be `qdrant` or `pgvector`.
    -   `REDIS_URL`: The connection string for Redis. The default should work.
    -   `RAE_LLM_BACKEND`: The LLM backend to use. Options are `gemini`, `openai`, `ollama`, `anthropic`.
    -   `RAE_LLM_MODEL_DEFAULT`: The default model to use for the selected backend.
    -   `OAUTH_DOMAIN`: **(Required)** The domain of your OAuth2 provider (e.g., from Auth0).
    -   `OAUTH_AUDIENCE`: **(Required)** The API audience identifier from your OAuth2 provider.
    -   API keys for your chosen LLM provider (e.g., `OPENAI_API_KEY`).

## 3. Run the API

Now you can run the FastAPI-based Memory API.

1.  **Create a virtual environment and install dependencies**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r apps/memory_api/requirements.txt
    ```

2.  **Run database migrations**:
    The `make db-init` command will initialize the database schema.
    ```bash
    make db-init
    ```

3.  **Start the API server**:
    ```bash
    uvicorn apps.memory-api.main:app --reload
    ```
    The API will be available at `http://localhost:8000`.

## 4. First Interaction

You can interact with the RAE API using `curl` or the Python SDK.

### Using `curl`

To interact with the API, you now need to provide a valid JWT from your OAuth2 provider in the `Authorization` header.

**Note:** The following example assumes you have a valid JWT access token. How you obtain this token depends on your specific OAuth2 provider and flow (e.g., Client Credentials, Authorization Code).

```bash
# Replace YOUR_ACCESS_TOKEN with a valid JWT
export RAE_ACCESS_TOKEN="YOUR_ACCESS_TOKEN"

curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RAE_ACCESS_TOKEN" \
  -H "X-Tenant-ID: getting-started-tenant" \
  -d '{
    "layer": "episodic",
    "type": "event",
    "content": "The user is following the getting started guide.",
    "tags": ["onboarding", "tutorial"]
  }'
```

And then query for it:

```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RAE_ACCESS_TOKEN" \
  -H "X-Tenant-ID: getting-started-tenant" \
  -d '{
    "query": "What is the user doing?"
  }'
```

### Using the Python SDK

The Python SDK provides a more convenient way to interact with the API.

1.  **Install the SDK**:
    ```bash
    pip install ./sdk/python/rae_memory_sdk
    ```

2.  **Use the SDK in your code**:
    ```python
    from rae_memory_sdk import RAEClient

    client = RAEClient(
        base_url="http://localhost:8000",
        tenant_id="sdk-tenant",
    )

    # Store a memory
    client.store_memory(
        layer="episodic",
        type="event",
        content="The user is testing the Python SDK.",
        tags=["sdk", "test"]
    )

    # Query for memories
    response = client.query_memory(
        query="What is the user testing?",
        top_k=1
    )

    print(response)
    ```

## Where to Go Next

Now that you have a running RAE instance, you can explore more advanced topics:

-   **Examples**: Check out the `examples/` directory for more detailed use cases.
-   **Integrations**: The `integrations/` directory shows how to use RAE with frameworks like LangChain and LlamaIndex.
-   **Evaluation**: The `eval/` directory contains tools for evaluating the performance of the memory system.