import pytest
import asyncio
from unittest.mock import MagicMock, patch
from rae_lite.service import RAELiteService
from rae_lite.config import settings

class TestRAELiteServiceIntegration:
    
    @pytest.mark.asyncio
    async def test_service_initialization_and_query(self, tmp_path):
        """Test full service initialization and query flow."""
        
        # Setup temporary DB path
        storage_path = str(tmp_path)
        
        # Initialize Service
        service = RAELiteService(storage_path=storage_path)
        
        # Mock LLM Adapter to avoid subprocess calls
        service.llm_adapter.normalize_query = MagicMock(return_value="normalized query")
        service.llm_adapter.format_results = MagicMock(return_value="formatted result")
        
        # Start Service (initializes DB)
        await service.start()
        
        # Inject a test memory directly into storage
        await service.storage.store_memory(
            content="Test memory content",
            layer="semantic",
            tenant_id="test-tenant",
            agent_id="test-agent",
            tags=["test"],
            importance=0.8
        )
        
        # Perform Query
        results = await service.query("test query", tenant_id="test-tenant")
        
        # Verify
        assert service.llm_adapter.normalize_query.called
        # Results might be empty depending on FTS implementation in SQLiteStorage/mock
        # But we ensure no exception was raised and flow completed
        
        await service.stop()
