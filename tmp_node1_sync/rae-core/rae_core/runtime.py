import structlog

from rae_core.interfaces.agent import BaseAgent
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.interaction import AgentAction, AgentActionType, RAEInput

logger = structlog.get_logger(__name__)


class RAERuntime:
    """
    The Operating System for Agents.
    Orchestrates the lifecycle: Input -> Agent -> Action -> Memory -> Output.
    """

    def __init__(self, storage: IMemoryStorage, agent: BaseAgent | None = None):
        self.storage = storage
        self.agent = agent

    async def process(self, input_payload: RAEInput) -> AgentAction:
        """
        Executes the agent within the RAE boundaries.
        Enforces memory persistence and policy checks.
        """
        if not self.agent:
            raise RuntimeError("No agent configured for Runtime")

        logger.info("rae_runtime_start", request_id=str(input_payload.request_id))

        # 1. Execute Agent (Pure Function)
        try:
            action = await self.agent.run(input_payload)
        except Exception as e:
            logger.error("agent_execution_failed", error=str(e))
            raise RuntimeError(f"Agent execution failed: {e}")

        # 2. Validation (Architecture Enforcement)
        if not isinstance(action, AgentAction):
            raise TypeError(
                f"Agent returned {type(action)} instead of AgentAction. "
                "Direct string return is FORBIDDEN."
            )

        # 3. Memory Hook (The "Side Effect")
        # Agent doesn't know this happens.
        await self._handle_memory_policy(input_payload, action)

        logger.info(
            "rae_runtime_success", action_type=action.type, confidence=action.confidence
        )

        return action

    async def _handle_memory_policy(self, input_payload: RAEInput, action: AgentAction):
        """
        Decides if and how to store the action in memory.
        This represents the 'Memory Policy Engine'.
        """

        # Default Policy: Store "Final Answers" as Episodic Memory
        agent_id = input_payload.context.get("agent_id", "agent-runtime")
        project = input_payload.context.get("project")

        if action.type == AgentActionType.FINAL_ANSWER:
            logger.info("memory_policy_triggered", rule="final_answer_store")

            await self.storage.store_memory(
                content=str(action.content),
                layer="episodic",
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=["rae-first", "final_answer"] + action.signals,
                metadata={
                    "request_id": str(input_payload.request_id),
                    "confidence": action.confidence,
                    "reasoning": action.reasoning,
                    "input_preview": input_payload.content[:50],
                },
                project=project,
                session_id=input_payload.context.get("session_id"),
                source="RAERuntime",
            )

        # Policy: Store "Thoughts" if they contain crucial decisions
        elif action.type == AgentActionType.THOUGHT and "decision" in action.signals:
            logger.info("memory_policy_triggered", rule="critical_thought_store")

            await self.storage.store_memory(
                content=f"Reasoning: {action.reasoning} | Content: {str(action.content)}",
                layer="working",
                tenant_id=input_payload.tenant_id,
                agent_id=agent_id,
                tags=["rae-first", "thought", "decision"],
                metadata={
                    "request_id": str(input_payload.request_id),
                    "confidence": action.confidence,
                },
                project=input_payload.context.get("project"),
                session_id=input_payload.context.get("session_id"),
                source="RAERuntime",
            )

        # TODO: Add more rules here (e.g., Tool Calls logging)
