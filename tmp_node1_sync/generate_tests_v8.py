# generate_tests_v8.py
import zipfile

# --- 1. CONFTEST (Bez zmian - działa poprawnie z V7) ---
CONFTEST_PY = """
import sys
import os
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.memory_api.main import app
from apps.memory_api.dependencies import get_api_key
from apps.memory_api.security import auth

sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(autouse=True)
def mock_env_and_settings(monkeypatch):
    envs = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_pass",
        "QDRANT_HOST": "localhost",
        "REDIS_URL": "redis://localhost:6379/0",
        "RAE_LLM_BACKEND": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "API_KEY": "test-api-key",
        "OAUTH_ENABLED": "False"
    }
    for k, v in envs.items():
        monkeypatch.setenv(k, v)

    with patch("apps.memory_api.config.settings") as mock_settings:
        mock_settings.API_KEY = "test-api-key"
        mock_settings.POSTGRES_HOST = "localhost"
        mock_settings.POSTGRES_DB = "test"
        mock_settings.POSTGRES_USER = "user"
        mock_settings.POSTGRES_PASSWORD = "pass"
        mock_settings.QDRANT_HOST = "localhost"
        mock_settings.RERANKER_API_URL = "http://reranker"
        mock_settings.MEMORY_API_URL = "http://memory"
        mock_settings.RAE_LLM_MODEL_DEFAULT = "gpt-4"
        yield mock_settings

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_api_key] = lambda: "test-api-key"
    app.dependency_overrides[auth.verify_token] = lambda: {"sub": "test-user", "scope": "admin"}
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_app_state_pool():
    mock_pool = MagicMock()
    mock_pool.fetch = AsyncMock()
    mock_pool.fetchrow = AsyncMock()
    mock_pool.execute = AsyncMock()
    mock_pool.close = AsyncMock()

    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock()
    mock_conn.fetch = AsyncMock()
    mock_conn.fetchval = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_transaction_cm = AsyncMock()
    mock_transaction_cm.__aenter__.return_value = None
    mock_transaction_cm.__aexit__.return_value = None
    mock_conn.transaction.return_value = mock_transaction_cm

    mock_acquire_cm = AsyncMock()
    mock_acquire_cm.__aenter__.return_value = mock_conn
    mock_acquire_cm.__aexit__.return_value = None

    mock_pool.acquire.return_value = mock_acquire_cm

    app.state.pool = mock_pool
    yield mock_pool
    del app.state.pool
"""

# --- 2. API MEMORY (Poprawka payloadu importance) ---
TEST_API_MEMORY_PY = """
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from apps.memory_api.main import app
from apps.memory_api.models import ScoredMemoryRecord
from datetime import datetime

client = TestClient(app)

@pytest.fixture
def mock_vector_store():
    with patch("apps.memory_api.api.v1.memory.get_vector_store") as mock:
        instance = AsyncMock()
        instance.upsert = AsyncMock()
        instance.query = AsyncMock(return_value=[])
        instance.delete = AsyncMock()

        mock.return_value = instance
        yield instance

@pytest.fixture
def mock_embedding_service():
    with patch("apps.memory_api.api.v1.memory.get_embedding_service") as mock:
        instance = MagicMock()
        instance.generate_embeddings.return_value = [[0.1] * 384]
        mock.return_value = instance
        yield instance

@pytest.mark.asyncio
async def test_store_memory_success(mock_app_state_pool, mock_vector_store, mock_embedding_service):
    mock_conn = mock_app_state_pool.acquire.return_value.__aenter__.return_value

    mock_conn.fetchrow.return_value = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "created_at": datetime.now(),
        "last_accessed_at": datetime.now(),
        "usage_count": 0
    }

    # POPRAWKA: Dodano 'importance', aby uniknąć błędu walidacji w API
    payload = {
        "content": "Test content",
        "source": "cli",
        "layer": "ltm",
        "tags": ["test"],
        "project": "default",
        "importance": 0.5
    }

    response = client.post(
        "/v1/memory/store",
        json=payload,
        headers={"X-Tenant-Id": "test-tenant"}
    )

    if response.status_code != 200:
        print("STORE ERROR:", response.json())

    assert response.status_code == 200
    assert response.json()["id"] == "123e4567-e89b-12d3-a456-426614174000"

@pytest.mark.asyncio
async def test_query_memory_success(mock_app_state_pool, mock_vector_store, mock_embedding_service):
    record = ScoredMemoryRecord(
        id="mem-1",
        content="Found",
        score=0.95,
        importance=0.5,
        layer="ltm",
        tags=[],
        source="src",
        project="proj",
        timestamp=datetime.now(),
        last_accessed_at=datetime.now(),
        usage_count=10
    )

    mock_vector_store.query.return_value = [record]

    payload = {"query_text": "test query", "k": 1}

    response = client.post(
        "/v1/memory/query",
        json=payload,
        headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1

@pytest.mark.asyncio
async def test_delete_memory_success(mock_app_state_pool, mock_vector_store):
    mock_conn = mock_app_state_pool.acquire.return_value.__aenter__.return_value
    mock_conn.execute.return_value = "DELETE 1"

    response = client.delete(
        "/v1/memory/delete?memory_id=mem-1",
        headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
"""

# --- 3. SERVICES BUDGET (Poprawka importu MagicMock) ---
TEST_SERVICES_BUDGET_PY = """
import pytest
# POPRAWKA: Dodano MagicMock do importów
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from apps.memory_api.services import budget_service
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_check_budget():
    mock_pool = MagicMock()
    mock_pool.fetchrow = AsyncMock()

    mock_pool.fetchrow.return_value = {
        "id": "b1", "tenant_id": "t1", "project_id": "p1",
        "monthly_limit": 10.0, "monthly_usage": 5.0,
        "daily_limit": 1.0, "daily_usage": 0.5,
        "last_usage_at": datetime.now()
    }

    await budget_service.check_budget(mock_pool, "t1", "p1", 0.1)

@pytest.mark.asyncio
async def test_check_budget_fail():
    mock_pool = MagicMock()
    mock_pool.fetchrow = AsyncMock()

    mock_pool.fetchrow.return_value = {
        "id": "b1", "tenant_id": "t1", "project_id": "p1",
        "monthly_limit": 10.0, "monthly_usage": 5.0,
        "daily_limit": 1.0, "daily_usage": 0.9,
        "last_usage_at": datetime.now()
    }

    with pytest.raises(HTTPException) as exc:
        await budget_service.check_budget(mock_pool, "t1", "p1", 0.2)
    assert exc.value.status_code == 402
"""

# --- RESZTA BEZ ZMIAN ---
TEST_API_AGENT_PY = """
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.memory_api.api.v1.agent import execute
from apps.memory_api.models import AgentExecuteRequest
from apps.memory_api.services.llm.base import LLMResult, LLMResultUsage
from fastapi import Request

@pytest.mark.asyncio
async def test_agent_execute_direct(mock_app_state_pool):
    with patch("apps.memory_api.api.v1.agent.get_context_cache") as mock_get_cache, \
         patch("apps.memory_api.api.v1.agent.get_embedding_service") as mock_embed, \
         patch("apps.memory_api.api.v1.agent.get_vector_store") as mock_vec, \
         patch("apps.memory_api.api.v1.agent.get_llm_provider") as mock_llm, \
         patch("apps.memory_api.api.v1.agent._update_memory_access_stats", new=AsyncMock()), \
         patch("httpx.AsyncClient") as mock_httpx:

        mock_cache_instance = MagicMock()
        mock_cache_instance.get_context.return_value = "Mocked Context"
        mock_get_cache.return_value = mock_cache_instance

        mock_embed.return_value.generate_embeddings.return_value = [[0.1]*384]

        mock_vec_inst = AsyncMock()
        mock_vec_inst.query = AsyncMock(return_value=[])
        mock_vec.return_value = mock_vec_inst

        mock_llm_inst = MagicMock()
        mock_llm_inst.generate = AsyncMock(return_value=LLMResult(
            text="Direct Answer",
            usage=LLMResultUsage(prompt_tokens=10, candidates_tokens=10, total_tokens=20),
            model_name="gpt-4",
            finish_reason="stop"
        ))
        mock_llm.return_value = mock_llm_inst

        mock_hclient = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_hclient
        mock_hclient.post.return_value.json = AsyncMock(return_value={"items": []})

        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "t1"
        mock_request.app.state.pool = mock_app_state_pool

        payload = AgentExecuteRequest(
            tenant_id="t1",
            project="p1",
            prompt="Hi"
        )

        if hasattr(execute, "__wrapped__"):
            original_func = execute.__wrapped__
        else:
            original_func = execute

        response = await original_func(payload, mock_request)

        assert response.answer == "Direct Answer"
        mock_cache_instance.get_context.assert_called()
"""

TEST_API_CACHE_PY = """
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from apps.memory_api.main import app

client = TestClient(app)

@patch("apps.memory_api.api.v1.cache.rebuild_cache.delay")
def test_rebuild_cache(mock_task):
    response = client.post("/v1/cache/rebuild", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 202
    mock_task.assert_called_once()
"""

TEST_SERVICES_LLM_PY = """
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.memory_api.services.llm.openai import OpenAIProvider

@pytest.mark.asyncio
async def test_openai_generate():
    with patch("apps.memory_api.services.llm.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="Hello"), finish_reason="stop")]
        mock_resp.usage.prompt_tokens = 10
        mock_resp.usage.completion_tokens = 10
        mock_resp.usage.total_tokens = 20

        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        provider = OpenAIProvider(api_key="test")
        res = await provider.generate(system="sys", prompt="user", model="gpt-4")

        assert res.text == "Hello"
"""

TEST_SERVICES_REDIS_PY = """
import pytest
from unittest.mock import MagicMock, patch
from apps.memory_api.services.context_cache import ContextCache

@patch("apps.memory_api.services.context_cache.get_redis_client")
def test_context_cache_flow(mock_get_redis):
    mock_redis_instance = MagicMock()
    mock_get_redis.return_value = mock_redis_instance

    cache = ContextCache()
    cache.set_context("t1", "p1", "semantic", "data")
    mock_redis_instance.setex.assert_called_once()
"""

TEST_SERVICES_REFLECTION_PY = """
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.memory_api.services.reflection_engine import ReflectionEngine
from apps.memory_api.services.llm.base import LLMResult, LLMResultUsage

@pytest.mark.asyncio
async def test_reflection_flow():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_acquire_cm = AsyncMock()
    mock_acquire_cm.__aenter__.return_value = mock_conn
    mock_acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = mock_acquire_cm

    mock_conn.fetch.return_value = [{"id": "1", "content": "Event"}]

    engine = ReflectionEngine(mock_pool)
    engine.llm_provider = MagicMock()
    engine.llm_provider.generate = AsyncMock(return_value=LLMResult(
        text="Insight",
        usage=LLMResultUsage(prompt_tokens=1, candidates_tokens=1, total_tokens=2),
        model_name="gpt",
        finish_reason="stop"
    ))

    with patch("apps.memory_api.services.reflection_engine.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_http:

        mock_settings.API_KEY = "key"
        mock_settings.MEMORY_API_URL = "http://mem"
        mock_settings.RAE_LLM_MODEL_DEFAULT = "gpt"

        mock_http.return_value.__aenter__.return_value.post = AsyncMock()

        res = await engine.generate_reflection("p1", "t1")

        assert "Insight" in res
"""

TEST_RERANKER_PY = """
import sys
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

current_file = Path(__file__).resolve()
service_dir = current_file.parent.parent
sys.path.insert(0, str(service_dir))

try:
    from main import app
except ImportError:
    sys.path.append(str(service_dir))
    from main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
"""

# --- GENEROWANIE ZIP ---
file_structure = {
    "tests/conftest.py": CONFTEST_PY,
    "tests/api/v1/test_memory.py": TEST_API_MEMORY_PY,
    "tests/api/v1/test_agent.py": TEST_API_AGENT_PY,
    "tests/api/v1/test_cache.py": TEST_API_CACHE_PY,
    "tests/services/llm/test_providers.py": TEST_SERVICES_LLM_PY,
    "tests/services/test_context_cache.py": TEST_SERVICES_REDIS_PY,
    "tests/services/test_reflection_engine.py": TEST_SERVICES_REFLECTION_PY,
    "tests/services/test_budget_service.py": TEST_SERVICES_BUDGET_PY,
    "apps/reranker-service/tests/test_main.py": TEST_RERANKER_PY,
}


def create_zip():
    zip_filename = "rae_tests_v8.zip"
    print(f"Tworzenie {zip_filename}...")
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filepath, content in file_structure.items():
            print(f"Dodawanie: {filepath}")
            zipf.writestr(filepath, content.strip())
    print("Gotowe.")


if __name__ == "__main__":
    create_zip()
