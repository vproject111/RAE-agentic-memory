# RAE for Developers: Quick Start & API Integration

This guide provides developers with a comprehensive overview of how to set up, deploy, and integrate with the RAE (Reasoning and Action Engine).

## Quick Start: 5-Minute Hello World

This quick start uses the **RAE Lite** profile, which is the fastest way to get a functional RAE instance running on your local machine.

**Prerequisites:**
- Docker and Docker Compose installed.
- Git installed.

**Steps:**

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/dreamsoft-pro/RAE-agentic-memory.git
    cd RAE-agentic-memory
    ```

2.  **Choose and Start your RAE Environment:**

RAE offers several Docker Compose profiles tailored to different use cases. This allows you to run multiple environments (like `dev` and `lite`) simultaneously without conflicts.

### 1. Development Environment (Hot Reload)

This is the recommended setup for active development. It enables hot-reloading for rapid iteration.

-   **Purpose:** Actively write and test code.
-   **Features:** Hot-reloading, debug-level logging, development tools (`Adminer`).
-   **API Port:** `http://localhost:8001`
-   **Dashboard Port:** `http://localhost:8502`

**How to Run:**
```bash
# Start the development environment in the background
docker compose --profile dev up -d

# To stop
docker compose --profile dev down
```

### 2. Full RAE Environment

This is the complete, production-like stack with all services, including asynchronous workers and observability tools.

#### Option A: Running Standalone (on Default Ports)

Use this when you only need to run the full RAE stack by itself.

-   **Purpose:** Test the full application as it would run in a standard single-node production.
-   **API Port:** `http://localhost:8000`
-   **Dashboard Port:** `http://localhost:8501`
-   **Warning:** This will use default ports (`8000`, `5432`, etc.) and will conflict with other applications or Docker containers using them.

**How to Run:**
```bash
# Start the standard environment in the background
docker compose --profile standard up -d

# To stop
docker compose --profile standard down
```

#### Option B: Running Sandboxed (Side-by-side with Dev)

Use this to run a full RAE instance simultaneously with your `dev` environment without port conflicts.

-   **Purpose:** Test against a stable, full RAE version while actively developing.
-   **API Port:** `http://localhost:8020`
-   **Database Port:** `5450`

**How to Run:**
```bash
# Start the sandboxed full environment using its dedicated compose file
docker-compose -f docker-compose.sandbox-full.yml up -d

# To stop
docker-compose -f docker-compose.sandbox-full.yml down
```

### 3. RAE-Lite Environment

This is a lightweight, minimal-dependency version, perfect for quick tests or resource-constrained machines.

#### Option A: Running Sandboxed (Side-by-side, Default)

This is the default way to run `RAE-Lite` so it doesn't conflict with the `dev` or `standard` profiles.

-   **Purpose:** Quickly test core logic or run on a laptop.
-   **API Port:** `http://localhost:8008` (by default)

**How to Run:**
```bash
# Ensure your .env file has API keys (e.g., OPENAI_API_KEY)
# Start the lite environment in the background
docker compose --profile lite up -d

# To stop
docker compose --profile lite down
```

#### Option B: Running on a Custom Port (e.g., Default Port 8000)

If you are only running the `lite` profile and want it to use the default API port `8000`, you can easily configure it.

**Method 1: Using an Environment Variable (Recommended)**
Run the `docker compose` command with the `RAE_LITE_PORT` variable set.
```bash
# This will start the lite API on http://localhost:8000
RAE_LITE_PORT=8000 docker compose --profile lite up -d
```

**Method 2: Using the `.env` file**
Add the following line to your `.env` file at the root of the project. Docker Compose will automatically pick it up.
```
RAE_LITE_PORT=8000
```
Then run the standard command: `docker compose --profile lite up -d`.

### 4. Running Environments Simultaneously (Summary)

The port mapping is designed to allow you to run multiple environments at once. For example:
-   **Terminal 1 (Dev):** `docker compose --profile dev up -d` (API on port `8001`)
-   **Terminal 2 (Lite):** `docker compose --profile lite up -d` (API on port `8008`)
-   **Terminal 3 (Full Sandbox):** `docker-compose -f docker-compose.sandbox-full.yml up -d` (API on port `8020`)

All three environments can run side-by-side without interfering with each other.

3.  **Verify the services are running (for selected profile):**
    You can check the status of the containers:
    ```bash
    docker compose ps
    ```
    For the `standard` profile, you should be able to access the health check endpoint:
    [http://localhost:8000/health](http://localhost:8000/health)
    For the `dev` profile, you should be able to access:
    [http://localhost:8001/health](http://localhost:8001/health)
    For the `lite` profile, you should be able to access:
    [http://localhost:8008/health](http://localhost:8008/health)

4.  **Interact with the API using the Python SDK:**
    *(Assuming you have Python and `pip` installed on your host machine)*

    a. **Install the SDK:**
    ```bash
    pip install -e ./sdk/python/
    ```

    b. **Create a Python script (`hello_rae.py`):**
    ```python
    import asyncio
    from rae_memory_sdk.memory_client import MemoryClient, MemoryOperation

    async def main():
        # Connect to the local RAE API (adjust port for dev/lite profiles)
        # For standard: client = MemoryClient(base_url="http://localhost:8000")
        # For dev: client = MemoryClient(base_url="http://localhost:8001")
        # For lite: client = MemoryClient(base_url="http://localhost:8008")
        client = MemoryClient() # Default to http://localhost:8000 for standard example

        # Define a tenant and project
        tenant_id = "my-test-tenant"
        project_id = "my-first-project"

        # Add a memory
        memory_text = "The user is interested in learning about cognitive architectures."
        await client.add_memory(
            tenant_id,
            project_id,
            memory_text,
            importance=0.8,
            source="hello_world_script"
        )
        print(f"Added memory: '{memory_text}'")

        # Retrieve the memory
        query = "What is the user interested in?"
        results = await client.query_memory(tenant_id, project_id, query)

        print(f"\nQuerying for: '{query}'")
        if results:
            print("Found matching memories:")
            for res in results:
                print(f"- {res.content} (Score: {res.score:.2f})")
        else:
            print("No matching memories found.")

    if __name__ == "__main__":
        asyncio.run(main())

    ```

    c. **Run the script:**
    ```bash
    python hello_rae.py
    ```

You have now successfully added a memory to RAE and retrieved it!

---

## API Reference

For a complete list of all 96+ endpoints, including Memory, GraphRAG, Governance, and more, please refer to the full [API Documentation](../../API_DOCUMENTATION.md).

You can also browse the interactive Swagger UI locally at `http://localhost:8000/docs` (for standard profile) or `http://localhost:8001/docs` (for dev profile) or `http://localhost:8008/docs` (for lite profile) when the respective service is running.

---

## Combining Profiles

It's often useful to combine profiles for specific development or testing scenarios. For instance, you might want to run the full `dev` environment (with hot-reloading for API, ML, and Celery services) while still leveraging the lightweight `lite` database and vector store setup.

**How to Run (Combined Profiles):**
```bash
docker compose --profile dev --profile lite up -d

# To stop the combined profiles
docker compose --profile dev --profile lite down
```

This will bring up:
-   `rae-api-dev` (hot-reloading API on port 8001)
-   `ml-service-dev` (hot-reloading ML service on port 8003)
-   `celery-worker-dev` and `celery-beat-dev` (hot-reloading Celery services)
-   `rae-dashboard-dev` (hot-reloading Dashboard on port 8502)
-   `adminer-dev` (database UI on port 8080)
-   `ollama-dev` (local LLM on port 11434, if '--profile local-llm' is also included)
-   `rae-api-lite` (lightweight API on port 8008)
-   `postgres-lite`, `redis-lite`, `qdrant-lite` (lightweight database services)

### 4. Proxmox HA (High Availability)
For enterprise-grade, high-availability deployments, RAE can be deployed in a multi-node cluster using Proxmox. This setup involves load balancers, replicated services, and failover mechanisms.

**(TODO: Extract detailed steps from `docs/PRODUCTION_PROXMOX_HA.md` and add them here.)**

### 5. Advanced Deployment Scenarios
For specific infrastructure needs, consult our detailed guides:
- **[Single Node Production](../../docs/PRODUCTION_SINGLE_NODE.md)**: Standard reference architecture for bare-metal or VM deployment.
- **[Proxmox High Availability](../../docs/PRODUCTION_PROXMOX_HA.md)**: Clustering guide for zero-downtime environments.
- **[CI/CD Workflow](../../docs/CI_WORKFLOW.md)**: Deep dive into the continuous integration pipeline.

---

## Testing Strategy

Building reliable agents requires a robust testing culture. RAE provides specialized tools for testing non-deterministic behavior.

-   **[Agent Testing Guide](../../docs/AGENT_TESTING_GUIDE.md)**: How to write unit, integration, and e2e tests for agents.
-   **[Test Policy](../../docs/AGENTS_TEST_POLICY.md)**: Standards for test coverage and "Zero Flake" policy.

### Real-World Case Studies
See RAE in action optimizing its own code:
-   **[Autonomous Self-Optimization](../../docs/use-cases/SELF_OPTIMIZATION_LOOP.md)**: How RAE diagnosed a 20x latency regression and fixed it by tuning its Math Controller.
-   **[Strategic Reasoning Pivot](../../docs/use-cases/STRATEGIC_REASONING_PIVOT.md)**: How RAE saved resources by challenging a user request and proposing a better architectural solution.
-   **[Distributed Code Audit](../../docs/use-cases/DISTRIBUTED_CODE_AUDIT.md)**: Using Node1 (GPU) to audit code quality.

## Troubleshooting

Encountering issues? Check the **[Troubleshooting Guide](../../TROUBLESHOOTING.md)** for solutions to common problems like:
-   Database migration locks (`alembic` issues)
-   Vector store connection failures
-   Memory leaks in long-running workers

---

## Architecture Deep Dive

RAE follows a clean, 3-layer architecture pattern within its services:

**Repository Layer → Service Layer → Route Layer**

1.  **Repository Layer:**
    -   **Purpose:** Handles all direct communication with the database (PostgreSQL and Qdrant). It abstracts away the specifics of data storage and retrieval.
    -   **Example:** `apps/memory_api/repositories/memory_repository.py` contains methods like `insert_memory` and `query_memories_by_vector`.

2.  **Service Layer:**
    -   **Purpose:** Contains the core business logic of the application. It orchestrates calls to one or more repositories and implements the complex features of the engine.
    -   **Example:** `apps/memory_api/services/memory_scoring_v3.py` implements the hybrid math scoring model, and `apps/memory_api/services/reflection_engine_v2.py` implements the reflection logic.

3.  **Route Layer (API):**
    -   **Purpose:** Defines the external-facing API endpoints. It handles incoming HTTP requests, performs validation (using Pydantic), calls the relevant service layer methods, and formats the HTTP response.
    -   **Example:** `apps/memory_api/routes/memory.py` defines the `/v1/memory/query` endpoint, which calls the memory service to perform a search.

This separation of concerns makes the codebase modular, easier to test, and easier to maintain.

---

## Testing Your Integration

RAE includes a comprehensive testing suite. When developing an application that integrates with RAE, you should follow these testing principles:

-   **Phase 1 (Feature Branch):** Test only your new code. If you add a feature that interacts with RAE, write specific tests for that interaction. You can run a subset of tests quickly using `pytest --no-cov path/to/your/tests`.
-   **Phase 2 (Develop Branch):** Before merging to a main branch, run the full unit test suite using `make test-unit`. This ensures your changes have not caused regressions elsewhere in the system.
-   **Use Templates:** When adding new code, use the templates provided in the `.ai-templates/` directory to ensure consistency.

(For more details, see `docs/AGENTS_TEST_POLICY.md`.)
