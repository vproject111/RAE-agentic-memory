"""Unit tests for ContextEnvelope ingestion hardening (Stage 2 / L3)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.api.v2.memory import StoreMemoryRequestV2
from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.main import app
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.rae_core_service import RAECoreService
from rae_core.engine import RAEEngine
from rae_core.models.envelope import CodeAttribution, ContextEnvelope


@pytest.fixture
def mock_rae_service():
    service = MagicMock(spec=RAECoreService)
    service.store_memory = AsyncMock(return_value=str(uuid4()))
    return service


@pytest.fixture
def client_with_mock_service(mock_pool, mock_rae_service):
    with patch.dict(
        os.environ,
        {
            "POSTGRES_USER": "rae",
            "POSTGRES_PASSWORD": "rae_password",
            "POSTGRES_DB": "rae",
            "POSTGRES_HOST": "localhost",
            "RAE_DB_MODE": "ignore",
        },
    ):
        app.state.pool = mock_pool
        test_tenant = uuid4()
        app.dependency_overrides[get_rae_core_service] = lambda: mock_rae_service
        app.dependency_overrides[get_and_verify_tenant_id] = lambda: test_tenant

        with TestClient(app) as client:
            yield client, mock_rae_service, test_tenant

        app.dependency_overrides.clear()


def test_store_memory_request_model_with_envelope():
    envelope = ContextEnvelope(
        source_type="code",
        project="rae_suite",
        attribution=CodeAttribution(
            repository="RAE-Suite",
            branch="develop",
            file_path="rae_core/engine.py",
            language="python",
            class_name="RAEEngine",
            function_name="search_evidence",
        ),
    )

    req = StoreMemoryRequestV2(
        content="async def search_evidence(): pass",
        project="core",
        envelope=envelope,
    )

    assert req.envelope is not None
    assert req.envelope.attribution.class_name == "RAEEngine"
    assert req.envelope.attribution.function_name == "search_evidence"


def test_post_memory_passes_envelope_to_service(client_with_mock_service):
    client, mock_service, tenant_id = client_with_mock_service

    payload = {
        "content": "def calculate_loss(): return 0.0",
        "project": "ml-engine",
        "source": "git",
        "importance": 0.8,
        "envelope": {
            "source_type": "code",
            "project": "ml-engine",
            "attribution": {
                "repository": "RAE-Suite",
                "file_path": "ml/loss.py",
                "language": "python",
                "function_name": "calculate_loss",
            },
        },
    }

    response = client.post("/v2/memories/", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Memory stored in RAE-Core"

    mock_service.store_memory.assert_awaited_once()
    kwargs = mock_service.store_memory.await_args.kwargs
    assert kwargs["envelope"] is not None
    assert kwargs["envelope"].attribution.function_name == "calculate_loss"
    assert kwargs["project"] == "ml-engine"


@pytest.mark.asyncio
async def test_rae_core_service_auto_enriches_code_when_envelope_omitted():
    service = RAECoreService.__new__(RAECoreService)
    service.engine = MagicMock(spec=RAEEngine)
    service.engine.store_memory = AsyncMock(return_value="mem-123")
    service.websocket_service = None

    code_content = """
class DataPipeline:
    \"\"\"Handles ETL transformation.\"\"\"
    def transform(self, data):
        return data.strip()
"""

    mem_id = await service.store_memory(
        tenant_id="tenant-1",
        project="data-project",
        content=code_content,
        source="editor",
        importance=0.7,
        metadata={"file_path": "etl/pipeline.py"},
    )

    assert mem_id == "mem-123"
    service.engine.store_memory.assert_awaited_once()
    engine_call_kwargs = service.engine.store_memory.await_args.kwargs
    assert "envelope" in engine_call_kwargs["metadata"]
    env_data = engine_call_kwargs["metadata"]["envelope"]
    assert env_data["source_type"] == "code"
    assert env_data["attribution"]["class_name"] == "DataPipeline"
    assert env_data["attribution"]["function_name"] == "transform"
    assert env_data["attribution"]["language"] == "python"


@pytest.mark.asyncio
async def test_rae_engine_preserves_envelope_in_chunks():
    mock_storage = MagicMock()
    mock_storage.store_memory = AsyncMock(return_value=uuid4())
    mock_vector = MagicMock()
    mock_vector.store_vector = AsyncMock()
    mock_embedding = MagicMock()
    del mock_embedding.generate_all_embeddings
    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 384)

    engine = RAEEngine(
        memory_storage=mock_storage,
        vector_store=mock_vector,
        embedding_provider=mock_embedding,
    )

    envelope = ContextEnvelope(
        source_type="code",
        project="test_proj",
        attribution=CodeAttribution(
            repository="RAE-Suite",
            file_path="engine/test.py",
            class_name="TestClass",
        ),
    )

    await engine.store_memory(
        tenant_id="tenant-1",
        agent_id="agent-1",
        content="class TestClass: pass",
        envelope=envelope,
    )

    mock_storage.store_memory.assert_awaited()
    storage_kwargs = mock_storage.store_memory.await_args.kwargs
    assert "envelope" in storage_kwargs["metadata"]
    assert (
        storage_kwargs["metadata"]["envelope"]["attribution"]["class_name"]
        == "TestClass"
    )
