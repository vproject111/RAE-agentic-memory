"""Governance and action execution delegate for RAECoreService."""

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

import structlog

from rae_core.interfaces.agent import BaseAgent
from rae_core.models.interaction import AgentAction, AgentActionType, RAEInput

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class GovernanceDelegate:
    """Handles agent action execution, Hard Frames lifecycle, and autonomy governance."""

    def __init__(self, service: "RAECoreService"):
        self.service = service

    async def execute_action(
        self,
        tenant_id: str | UUID,
        agent_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        project: Optional[str] = None,
    ) -> AgentAction:
        """Execute an agent action through RAERuntime (RAE-First)."""
        service_ref = self.service

        class TransientAgent(BaseAgent):
            def __init__(self, s: "RAECoreService"):
                self.svc = s

            async def run(self, rae_input: RAEInput) -> AgentAction:
                from rae_core.context.builder import ContextBuilder

                builder = ContextBuilder(max_tokens=4000)
                agent_id_ctx = rae_input.context.get("agent_id", "default")
                project_ctx = rae_input.context.get("project", "default")

                search_results = await self.svc.engine.search_memories(
                    query=rae_input.content,
                    tenant_id=rae_input.tenant_id,
                    agent_id=agent_id_ctx,
                    project=project_ctx,
                    layer=None,
                    top_k=10,
                )

                context_text, _ = builder.build_context(
                    memories=search_results, query=rae_input.content
                )

                pressure_constraints = ""
                if self.svc.szubar_mode:
                    failures = await self.svc.engine.search_memories(
                        query=rae_input.content,
                        tenant_id=rae_input.tenant_id,
                        agent_id="default",
                        project=project_ctx,
                        layer=None,
                        top_k=5,
                        filters={"governance.is_failure": "true"},
                    )

                    if not failures:
                        failures = await self.svc.engine.search_memories(
                            query="*",
                            tenant_id=rae_input.tenant_id,
                            agent_id="default",
                            project=project_ctx,
                            layer=None,
                            top_k=5,
                            filters={"governance.is_failure": "true"},
                        )

                    if failures:
                        pressure_constraints = (
                            "\nCRITICAL: DO NOT REPEAT THESE FAILURES:\n"
                        )
                        for f in failures:
                            if isinstance(f, dict):
                                gov = f.get("governance") or {}
                                if isinstance(gov, str):
                                    try:
                                        import json

                                        gov = json.loads(gov)
                                    except Exception:
                                        gov = {}
                                trace = gov.get("failure_trace", "Unknown failure")
                                content = f.get("content", "Unknown error")
                                pressure_constraints += (
                                    f"- {content} (Reason: {trace})\n"
                                )

                system_prompt = (
                    "YOU ARE A RAE HIVE AGENT. YOU OPERATE WITHIN AN AGNOSTIC, DETERMINISTIC ENGINE.\n"
                    "CORE MANDATES:\n"
                    "1. MODEL AGNOSTIC: Do not assume specific LLM or embedding library.\n"
                    "2. ARCHITECTURAL PURITY: Follow RABO ontology and System 93 specs.\n"
                    "3. NO BLOAT: Favor algorithmic elegance over heavy libraries.\n\n"
                    f"RELEVANT PROJECT CONTEXT:\n{context_text}\n{pressure_constraints}\n\n"
                    f"Task: {rae_input.content}"
                )

                try:
                    import asyncio

                    if not self.svc.engine.llm_provider:
                        raise RuntimeError("LLM Provider not available (RAE-Lite Mode)")

                    llm_result = await asyncio.wait_for(
                        self.svc.engine.generate_text(
                            prompt=rae_input.content, system_prompt=system_prompt
                        ),
                        timeout=120.0,
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning("llm_call_failed", error=str(e))
                    if search_results:
                        llm_result = "" + str(search_results[0].get("content", ""))[:500]
                    else:
                        llm_result = (
                            f"I encountered an issue connecting to the model: {str(e)}."
                        )

                if not llm_result:
                    llm_result = "I couldn't generate a response."

                signals = []
                if "stability" in llm_result.lower():
                    signals.append("fallback")
                if "decision" in llm_result.lower() or "rule" in llm_result.lower():
                    signals.append("decision")

                return AgentAction(
                    type=AgentActionType.FINAL_ANSWER,
                    content=llm_result,
                    confidence=0.5 if "FALLBACK" in llm_result else 0.9,
                    reasoning=(
                        "LLM with Math Fallback"
                        if "FALLBACK" in llm_result
                        else "LLM generation"
                    ),
                    signals=signals,
                )

        self.service.runtime.agent = TransientAgent(service_ref)

        project_canonical = self.service.ingestion_delegate.resolve_project_context(
            project
        )
        agent_canonical = agent_id or "default"

        return await self.service.runtime.process(
            RAEInput(
                content=prompt,
                tenant_id=str(tenant_id),
                request_id=uuid4(),
                context={
                    "agent_id": agent_canonical,
                    "project": project_canonical,
                    "session_id": session_id or "default-session",
                    "metadata": metadata or {},
                },
            )
        )
