
import pytest
import asyncio
from uuid import uuid4
from apps.memory_api.services.rae_core_service import RAECoreService
from rae_core.models.interaction import RAEInput

@pytest.mark.asyncio
async def test_szubar_mode_activation():
    service = RAECoreService()
    assert service.szubar_mode is False
    service.enable_szubar_mode(True)
    assert service.szubar_mode is True

@pytest.mark.asyncio
async def test_szubar_weights_injection():
    service = RAECoreService()
    service.enable_szubar_mode(True)
    
    # We mock tuning_service to avoid complex setup
    class MockTuning:
        async def get_current_weights(self, tid):
            from rae_core.math.structure import ScoringWeights
            return ScoringWeights()
            
    service.tuning_service = MockTuning()
    
    # Test query_memories uses szubar weights
    # We just want to see if it reaches the point of using weights
    # Since we use InMemoryStorage, it will return empty list but we check if it doesn't crash
    response = await service.query_memories(tenant_id=str(uuid4()), project="test", query="hello")
    assert response.total_found == 0

@pytest.mark.asyncio
async def test_szubar_failure_injection(mocker):
    service = RAECoreService()
    service.enable_szubar_mode(True)
    
    tenant_id = str(uuid4())
    agent_id = "test_agent"
    
    # Store a failure memory
    await service.store_memory(
        tenant_id=tenant_id,
        project=agent_id,
        content="Tried to use library X",
        source="llm",
        governance={"is_failure": True, "failure_trace": "Library X is incompatible with Python 3.12"}
    )
    
    # Mock engine.generate_text to inspect the system_prompt
    mock_gen = mocker.patch.object(service.engine, "generate_text", return_value="OK")
    
    await service.execute_action(
        tenant_id=tenant_id,
        agent_id=agent_id,
        prompt="How to install libraries?"
    )
    
    # Inspect calls to generate_text
    args, kwargs = mock_gen.call_args
    system_prompt = kwargs.get("system_prompt", "")
    
    assert "DO NOT REPEAT THESE FAILURES" in system_prompt
    assert "Library X is incompatible with Python 3.12" in system_prompt

if __name__ == "__main__":
    asyncio.run(test_szubar_mode_activation())
    print("Basic activation test passed!")
