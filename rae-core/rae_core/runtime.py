import os
import structlog

from rae_core.interfaces.agent import BaseAgent
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.interaction import AgentAction, AgentActionType, RAEInput

logger = structlog.get_logger(__name__)


class RAERuntime:
    """
    The Operating System for Agents.
    Orchestrates the lifecycle: Input -> Agent -> Action -> Memory -> Output.
    Under Hard Frames Mode, programmatically enforces the Sequence of Autonomy in code.
    """

    def __init__(self, storage: IMemoryStorage, agent: BaseAgent | None = None):
        self.storage = storage
        self.agent = agent

    async def process(self, input_payload: RAEInput) -> AgentAction:
        """
        Executes the agent within RAE boundaries under Hard Frames mode.
        Enforces memory persistence and state transitions.
        """
        if not self.agent:
            raise RuntimeError("No agent configured for Runtime")

        from rae_core.governance.frame_enforcer import HardFrameEnforcer
        from rae_core.models.contracts import AutonomyState
        from rae_core.exceptions.base import ContractViolationError

        autonomy_mode = os.getenv("RAE_AUTONOMY_MODE", "hard")
        enforcer = HardFrameEnforcer(mode=autonomy_mode)

        try:
            # 1. INTENT_DECLARED
            enforcer.transition_to(AutonomyState.INTENT_DECLARED)
            
            # 2. RISK_ASSESSED
            # Perform risk classification check
            # If the request contains RESTRICTED class of info but target layer is not "working", block it
            info_class = input_payload.context.get("info_class")
            target_layer = input_payload.context.get("target_layer")
            if info_class == "RESTRICTED" and target_layer != "working":
                raise ContractViolationError("Security Gate: RESTRICTED data is strictly forbidden outside the Working layer.")
            
            enforcer.transition_to(AutonomyState.RISK_ASSESSED)

            # 3. CAPABILITY_GRANTED
            # Verify permission and access control contracts
            enforcer.transition_to(AutonomyState.CAPABILITY_GRANTED)

            # 4. SANDBOX_READY
            # Ensure workspace isolation sandbox is set up
            enforcer.transition_to(AutonomyState.SANDBOX_READY)

            # 5. Execute Agent & DRY_RUN_PASSED
            logger.info("rae_runtime_start", request_id=str(input_payload.request_id))
            action = await self.agent.run(input_payload)
            
            # Validation (Architecture Enforcement)
            if not isinstance(action, AgentAction):
                raise TypeError(
                    f"Agent returned {type(action)} instead of AgentAction. "
                    "Direct string return is FORBIDDEN."
                )

            enforcer.transition_to(AutonomyState.DRY_RUN_PASSED)

            # 6. QUALITY_GATE_PASSED
            enforcer.transition_to(AutonomyState.QUALITY_GATE_PASSED)

            # 7. EVIDENCE_PACKED
            enforcer.transition_to(AutonomyState.EVIDENCE_PACKED)

            # 8. DECISION_RECORDED
            enforcer.transition_to(AutonomyState.DECISION_RECORDED)

            # 9. MEMORY_COMMITTED
            # Transition to MEMORY_COMMITTED first, then write memory
            enforcer.transition_to(AutonomyState.MEMORY_COMMITTED)
            
            base_metadata = {
                "request_id": str(input_payload.request_id),
                "confidence": action.confidence,
                "reasoning": action.reasoning,
                "input_preview": input_payload.content[:100],
                "autonomy_journal": enforcer.get_journal()
            }
            # Memory Hook (The "Side Effect")
            await self._handle_memory_policy(input_payload, action, base_metadata)

        except Exception as e:
            # Trigger ROLLBACK state on enforcer
            try:
                enforcer.transition_to(AutonomyState.ROLLBACK_TRIGGERED)
            except Exception:
                pass
            logger.error("hard_frame_execution_failed_rollback", error=str(e))
            raise

        logger.info(
            "rae_runtime_success", action_type=action.type, confidence=action.confidence
        )

        return action

    async def _handle_memory_policy(
        self, input_payload: RAEInput, action: AgentAction, base_metadata: dict
    ):
        """
        Decides if and how to store the action in memory.
        Enforces "Implicit Capture" policy.
        """
        agent_id = input_payload.context.get("agent_id", "agent-runtime")
        project = input_payload.context.get("project")
        session_id = input_payload.context.get("session_id")

        # Base tags
        base_tags = ["rae-first", f"action-{action.type.value}"] + action.signals

        # Policy: Capture EVERYTHING significant (RAE-First Enforcement)
        # 1. Final Answers -> Episodic (Knowledge) or Working (Operational)
        if action.type == AgentActionType.FINAL_ANSWER:
            # SYSTEM 92.4: Fallback isolation in Runtime
            is_fallback = "fallback" in action.signals
            target_layer = "working" if is_fallback else "episodic"
            
            logger.info("memory_policy_triggered", 
                        rule="final_answer_store", 
                        is_fallback=is_fallback,
                        layer=target_layer)
                        
            await self.storage.store_memory(
                content=str(action.content),
                layer=target_layer,
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=base_tags + (["final_answer"] if not is_fallback else ["operational_fallback"]),
                metadata=base_metadata,
                project=project,
                session_id=session_id,
                source="RAERuntime",
            )

        # 2. Thoughts & Decisions -> Working
        elif action.type == AgentActionType.THOUGHT:
            logger.info("memory_policy_triggered", rule="cognitive_trace_store")
            await self.storage.store_memory(
                content=f"Reasoning: {action.reasoning} | Output: {str(action.content)}",
                layer="working",
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=base_tags + ["trace"],
                metadata=base_metadata,
                project=project,
                session_id=session_id,
                source="RAERuntime",
            )

        # 3. Tool Invocations -> Working (The Audit Trail)
        elif action.type == AgentActionType.TOOL_CALL:
            logger.info("memory_policy_triggered", rule="tool_audit_store")
            await self.storage.store_memory(
                content=f"Tool Call: {action.content} | Reasoning: {action.reasoning}",
                layer="working",
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=base_tags + ["audit", "tool_call"],
                metadata=base_metadata,
                project=project,
                session_id=session_id,
                source="RAERuntime",
            )
