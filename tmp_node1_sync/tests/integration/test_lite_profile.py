"""
Integration tests for RAE Lite Profile deployment.

These tests verify that the docker-compose.test-sandbox.yml configuration works correctly
and all core services are operational.

Requirements:
- Docker and docker-compose installed
- .env file configured with LLM API key
- Ports 8000, 5432, 6333, 6379 available

Usage:
    pytest tests/integration/test_lite_profile.py -v
"""

import os
import subprocess
import time

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def lite_profile_services():
    """
    Start docker-compose.test-sandbox.yml services for integration testing.
    """
    # Define custom ports for the sandbox to avoid conflicts with running RAE
    env = os.environ.copy()
    env["RAE_LITE_PORT"] = "8010"
    env["RAE_LITE_PG_PORT"] = "5440"
    env["RAE_LITE_REDIS_PORT"] = "6390"
    env["RAE_LITE_QDRANT_PORT"] = "6340"
    env["RAE_LITE_QDRANT_GRPC_PORT"] = "6341"

    # Check if docker compose is available
    docker_compose_check = subprocess.run(
        ["docker", "compose", "version"], capture_output=True
    )
    if docker_compose_check.returncode != 0:
        pytest.skip("Skipping lite profile tests: docker compose not available")

    # Start services with a specific project name for isolation
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "up",
            "-d",
        ],
        check=True,
        capture_output=True,
        env=env,
    )

    # Wait for services to be ready (up to 180 seconds)
    max_retries = 90
    retry_count = 0
    api_ready = False

    api_port = "8010"

    while retry_count < max_retries and not api_ready:
        try:
            response = httpx.get(f"http://127.0.0.1:{api_port}/health", timeout=5.0)
            if response.status_code == 200:
                api_ready = True
                break
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.RequestError,
        ):
            pass

        retry_count += 1
        time.sleep(2)

    if not api_ready:
        # Cleanup on failure
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.test-sandbox.yml",
                "-p",
                "rae-lite-sandbox",
                "down",
                "-v",
            ],
            capture_output=True,
            env=env,
        )
        pytest.fail(f"RAE API failed to start on port {api_port} within 60 seconds")

    # --- SEEDING DATABASE FOR TESTS ---
    # Ensure tenant and user role exist so tests don't get 403/500
    import asyncio
    from uuid import UUID, uuid4

    import asyncpg

    async def seed_sandbox():
        try:
            # Use port from env (5440)
            conn = await asyncpg.connect("postgresql://rae:rae@localhost:5440/rae")

            # 1. Create Default Tenant
            tenant_id = "00000000-0000-0000-0000-000000000000"
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM tenants WHERE id = $1)", UUID(tenant_id)
            )
            if not exists:
                await conn.execute(
                    "INSERT INTO tenants (id, name, tier) VALUES ($1, $2, 'enterprise')",
                    UUID(tenant_id),
                    "Sandbox Tenant",
                )

            # 2. Grant Owner Role to 'apikey_secret' (User ID for 'secret' API key)
            await conn.execute(
                """
                INSERT INTO user_tenant_roles
                (id, user_id, tenant_id, role, project_ids, assigned_at, assigned_by)
                VALUES ($1, $2, $3, $4, $5, NOW(), $6)
                ON CONFLICT (user_id, tenant_id)
                DO UPDATE SET role = $4
            """,
                uuid4(),
                "apikey_secret",
                UUID(tenant_id),
                "owner",
                [],
                "test-setup",
            )

            await conn.close()
        except Exception as e:
            print(f"Warning: Failed to seed sandbox DB: {e}")
            # Don't fail here, maybe it worked or API handles it

    asyncio.run(seed_sandbox())
    # ----------------------------------

    # Services are ready
    yield

    # Teardown: Stop services and remove volumes
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "down",
            "-v",
        ],
        capture_output=True,
        env=env,
    )


def test_lite_profile_health_check(lite_profile_services):
    """Test that API health endpoint is accessible"""
    api_port = "8010"
    response = httpx.get(f"http://127.0.0.1:{api_port}/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]


def test_lite_profile_api_docs(lite_profile_services):
    """Test that API documentation is accessible"""
    api_port = "8010"
    response = httpx.get(f"http://127.0.0.1:{api_port}/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_lite_profile_store_memory(lite_profile_services):
    """Test storing a memory via API"""
    api_port = "8010"
    payload = {
        "content": "Integration test memory for RAE Lite Profile",
        "source": "integration-test",
        "layer": "episodic",
        "importance": 0.5,
        "tags": ["test", "integration"],
    }

    response = httpx.post(
        f"http://127.0.0.1:{api_port}/v1/memory/store",
        json=payload,
        headers={
            "X-Tenant-Id": "00000000-0000-0000-0000-000000000000",
            "X-API-Key": "secret",
        },
        timeout=10.0,
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert len(data["id"]) > 0


def test_lite_profile_query_memory(lite_profile_services):
    """Test querying memories via API"""
    api_port = "8010"
    # First, store a memory
    store_payload = {
        "content": "Test memory for query operation",
        "source": "integration-test",
        "layer": "episodic",
        "importance": 0.7,
        "tags": ["querytest"],
    }

    store_response = httpx.post(
        f"http://127.0.0.1:{api_port}/v1/memory/store",
        json=store_payload,
        headers={
            "X-Tenant-Id": "00000000-0000-0000-0000-000000000000",
            "X-API-Key": "secret",
        },
        timeout=10.0,
    )
    assert store_response.status_code == 200

    # Wait a moment for indexing
    time.sleep(1)

    # Query for the memory
    query_payload = {"query_text": "test memory query", "k": 5}

    response = httpx.post(
        f"http://127.0.0.1:{api_port}/v1/memory/query",
        json=query_payload,
        headers={
            "X-Tenant-Id": "00000000-0000-0000-0000-000000000000",
            "X-API-Key": "secret",
        },
        timeout=10.0,
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_lite_profile_services_running():
    """Test that all required Lite Profile services are running"""
    # Check services via docker compose
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "ps",
            "--services",
        ],
        capture_output=True,
        text=True,
    )

    services = result.stdout.strip().split("\n")

    # Expected services in Lite Profile
    expected_services = ["rae-api-lite", "postgres-lite", "qdrant-lite", "redis-lite"]

    for service in expected_services:
        assert service in services, f"Service {service} not found in running services"


def test_lite_profile_postgres_accessible():
    """Test that PostgreSQL is accessible"""
    # This is a basic check that postgres container is running
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "ps",
            "postgres-lite",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
    )

    assert "running" in result.stdout.lower() or "up" in result.stdout.lower()


def test_lite_profile_qdrant_accessible():
    """Test that Qdrant vector database is accessible"""
    try:
        # Check port from fixture (8010 used for API, but 6340 used for Qdrant)
        port = "6340"
        response = httpx.get(f"http://127.0.0.1:{port}/", timeout=5.0)
        assert response.status_code == 200
    except httpx.ConnectError:
        pytest.fail(f"Qdrant is not accessible on port {port}")


def test_lite_profile_redis_accessible():
    """Test that Redis cache is accessible"""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "ps",
            "redis-lite",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
    )

    assert "running" in result.stdout.lower() or "up" in result.stdout.lower()


def test_lite_profile_no_ml_service():
    """Verify that ML service is NOT running in Lite Profile"""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "ps",
            "--services",
        ],
        capture_output=True,
        text=True,
    )

    services = result.stdout.strip().split("\n")

    # These services should NOT be present in Lite Profile
    unwanted_services = ["ml-service", "celery-worker", "celery-beat", "rae-dashboard"]

    for service in unwanted_services:
        assert (
            service not in services
        ), f"Service {service} should not be in Lite Profile"


def test_lite_profile_resource_efficiency():
    """Verify that Lite Profile uses less resources than full stack"""
    # Check container count
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "ps",
            "--services",
        ],
        capture_output=True,
        text=True,
    )

    service_count = len(result.stdout.strip().split("\n"))

    # Lite Profile should have exactly 4 services (API, PostgreSQL, Qdrant, Redis)
    assert service_count == 4, f"Expected 4 services, found {service_count}"


@pytest.mark.skipif(
    subprocess.run(["docker", "compose", "version"], capture_output=True).returncode
    != 0,
    reason="docker compose not available",
)
def test_lite_profile_config_valid():
    """Test that docker-compose.test-sandbox.yml is valid"""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test-sandbox.yml",
            "-p",
            "rae-lite-sandbox",
            "config",
        ],
        capture_output=True,
    )

    assert result.returncode == 0, "docker-compose.test-sandbox.yml has invalid syntax"
