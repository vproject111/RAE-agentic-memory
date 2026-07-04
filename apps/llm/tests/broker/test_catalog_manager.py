import os
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from apps.llm.broker import ModelCatalogManager
from rae_core.llm import ModelDescriptor

@pytest.mark.asyncio
async def test_model_catalog_manager_static_fallback(tmp_path):
    cache_file = str(tmp_path / "cache.json")
    manager = ModelCatalogManager(cache_file_path=cache_file)
    
    with patch.object(manager, "_get_redis", return_value=None):
        models = await manager.get_models("openai")
        
        assert len(models) > 0
        assert any(m.id == "gpt-4o" for m in models)
        assert isinstance(models[0], ModelDescriptor)

@pytest.mark.asyncio
async def test_model_catalog_manager_local_cache_read(tmp_path):
    cache_file = str(tmp_path / "cache.json")
    cached_data = {
        "openai": [
            {"id": "gpt-custom", "name": "Custom Model", "provider": "openai", "context_window": 8000, "max_tokens": 1000}
        ]
    }
    with open(cache_file, "w") as f:
        json.dump(cached_data, f)
        
    manager = ModelCatalogManager(cache_file_path=cache_file)
    with patch.object(manager, "_get_redis", return_value=None):
        models = await manager.get_models("openai")
        assert len(models) == 1
        assert models[0].id == "gpt-custom"
        assert models[0].name == "Custom Model"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_model_catalog_manager_refresh(mock_get, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cache_file = str(tmp_path / "cache.json")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "gpt-fetched-1"},
            {"id": "gpt-fetched-2"}
        ]
    }
    mock_get.return_value = mock_resp
    
    manager = ModelCatalogManager(cache_file_path=cache_file)
    
    with patch.object(manager, "_get_redis", return_value=None):
        await manager.refresh_catalog_async()
        
        assert os.path.exists(cache_file)
        with open(cache_file, "r") as f:
            data = json.load(f)
            assert "openai" in data
            assert len(data["openai"]) == 2
            assert data["openai"][0]["id"] == "gpt-fetched-1"
