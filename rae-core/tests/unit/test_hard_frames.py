import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from rae_core.interfaces.agent import BaseAgent
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.interaction import AgentAction, AgentActionType, RAEInput
from rae_core.runtime import RAERuntime
from rae_core.governance.frame_enforcer import HardFrameEnforcer
from rae_core.models.contracts import AutonomyState
from rae_core.exceptions.base import ContractViolationError

class SimplePassedAgent(BaseAgent):
    async def run(self, input_payload: RAEInput) -> AgentAction:
        return AgentAction(
            type=AgentActionType.FINAL_ANSWER,
            content="Answer",
            confidence=0.9,
            reasoning="Simple logic",
            signals=["success"]
        )

def test_frame_enforcer_valid_sequence():
    enforcer = HardFrameEnforcer(mode="hard")
    assert enforcer.current_state == AutonomyState.INIT
    
    enforcer.transition_to(AutonomyState.INTENT_DECLARED)
    enforcer.transition_to(AutonomyState.RISK_ASSESSED)
    enforcer.transition_to(AutonomyState.CAPABILITY_GRANTED)
    enforcer.transition_to(AutonomyState.SANDBOX_READY)
    enforcer.transition_to(AutonomyState.DRY_RUN_PASSED)
    enforcer.transition_to(AutonomyState.QUALITY_GATE_PASSED)
    enforcer.transition_to(AutonomyState.EVIDENCE_PACKED)
    enforcer.transition_to(AutonomyState.DECISION_RECORDED)
    enforcer.transition_to(AutonomyState.MEMORY_COMMITTED)
    
    assert enforcer.current_state == AutonomyState.MEMORY_COMMITTED

def test_frame_enforcer_invalid_sequence_raises_error():
    enforcer = HardFrameEnforcer(mode="hard")
    
    # Skip INTENT_DECLARED and try to jump directly to RISK_ASSESSED
    with pytest.raises(ContractViolationError) as exc:
        enforcer.transition_to(AutonomyState.RISK_ASSESSED)
    
    assert "Invalid state transition requested" in str(exc.value)

@pytest.mark.asyncio
async def test_runtime_restricted_data_gate_blocks():
    storage = MagicMock(spec=IMemoryStorage)
    agent = SimplePassedAgent()
    runtime = RAERuntime(storage, agent)
    
    payload = RAEInput(
        request_id=uuid4(),
        tenant_id="t1",
        content="Sensitive info",
        context={"info_class": "RESTRICTED", "target_layer": "episodic"}  # RESTRICTED data outside Working layer
    )
    
    with pytest.raises(ContractViolationError) as exc:
        await runtime.process(payload)
        
    assert "RESTRICTED data is strictly forbidden outside the Working layer" in str(exc.value)

@pytest.mark.asyncio
async def test_runtime_valid_autonomy_journey():
    storage = MagicMock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock()
    agent = SimplePassedAgent()
    runtime = RAERuntime(storage, agent)
    
    payload = RAEInput(
        request_id=uuid4(),
        tenant_id="t1",
        content="Normal text",
        context={"info_class": "PUBLIC", "target_layer": "episodic"}
    )
    
    action = await runtime.process(payload)
    assert action.content == "Answer"
    
    # Check that store_memory was called and the metadata includes autonomy_journal
    storage.store_memory.assert_called_once()
    call_kwargs = storage.store_memory.call_args[1]
    autonomy_journal = call_kwargs["metadata"]["autonomy_journal"]
    
    assert "INIT" in autonomy_journal
    assert "MEMORY_COMMITTED" in autonomy_journal
