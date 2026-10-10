"""Memory ingestion delegate for RAECoreService."""

import asyncio
from typing import TYPE_CHECKING, Optional
from uuid import UUID

import structlog

from rae_core.exceptions.base import (
    ContractViolationError,
    SecurityPolicyViolationError,
)
from rae_core.models.envelope import ContextEnvelope
from rae_core.types.enums import InformationClass, MemoryLayer

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class MemoryIngestionDelegate:
    """Handles memory ingestion, policy enforcement, and provenance tracking."""

    def __init__(self, service: "RAECoreService"):
        self.service = service

    def enforce_security_policy(
        self,
        info_class: str,
        target_layer: str | MemoryLayer,
        tenant_id: str = "unknown",
    ) -> None:
        """Enforce ISO 27000 security policies."""
        layer_value = (
            target_layer.value
            if isinstance(target_layer, MemoryLayer)
            else target_layer
        )
        info_class_norm = info_class.lower()

        # 1. RESTRICTED: Only allowed in Working layer
        if info_class_norm == InformationClass.RESTRICTED:
            if layer_value != MemoryLayer.WORKING:
                if self.service.alert_service:
                    self.service.alert_service.trigger_security_alert(
                        tenant_id,
                        "RESTRICTED data promotion outside Working layer blocked",
                        {"layer": str(layer_value), "info_class": str(info_class_norm)},
                    )
                logger.error(
                    "security_policy_violation",
                    reason="RESTRICTED data blocked outside Working layer",
                    layer=layer_value,
                    info_class=info_class_norm,
                )
                raise SecurityPolicyViolationError(
                    f"Security Policy Violation: RESTRICTED data cannot be stored in {layer_value} layer. "
                    "Only 'working' layer is allowed for restricted information."
                )

        # 2. CONFIDENTIAL: Blocked from Semantic layer
        elif info_class_norm == InformationClass.CONFIDENTIAL:
            if layer_value == MemoryLayer.SEMANTIC:
                if self.service.alert_service:
                    self.service.alert_service.trigger_security_alert(
                        tenant_id,
                        "CONFIDENTIAL data promotion to Semantic layer blocked",
                        {"layer": str(layer_value), "info_class": str(info_class_norm)},
                    )
                logger.error(
                    "security_policy_violation",
                    reason="CONFIDENTIAL data blocked from Semantic layer",
                    layer=layer_value,
                    info_class=info_class_norm,
                )
                raise SecurityPolicyViolationError(
                    f"Security Policy Violation: CONFIDENTIAL data cannot be promoted to {layer_value} layer."
                )

        # 3. INTERNAL: Promotion to Semantic requires HITL/Sanitization (Policy placeholder)
        elif info_class_norm == InformationClass.INTERNAL:
            if layer_value == MemoryLayer.SEMANTIC:
                pass

    def detect_agentic_patterns(self, governance: dict, tags: list[str]) -> list[str]:
        """Detect agentic patterns and return updated tags."""
        pattern_type = governance.get("pattern_type")
        fields = governance.get("fields", {})

        if pattern_type == "prompt_chaining":
            chain_length = fields.get("chain_length", 0)
            if chain_length > 5:
                if "high_risk_sequence" not in tags:
                    tags.append("high_risk_sequence")
                    logger.warning(
                        "high_risk_sequence_detected", chain_length=chain_length
                    )

        elif pattern_type == "routing_decision":
            confidence = fields.get("decision_basis_confidence") or fields.get(
                "confidence", 1.0
            )
            if confidence < 0.5:
                if "hitl_review_required" not in tags:
                    tags.append("hitl_review_required")
                    logger.warning(
                        "low_confidence_routing_detected", confidence=confidence
                    )

        elif pattern_type == "tool_invocation":
            cost_metrics = fields.get("cost_metrics", {})
            token_count = cost_metrics.get("token_count", 0)
            if token_count > 10000:
                if "heavy_tool_use" not in tags:
                    tags.append("heavy_tool_use")
                    logger.info("heavy_tool_use_detected", token_count=token_count)

        elif pattern_type == "reflection":
            conf_before = fields.get("confidence_before", 1.0)
            conf_after = fields.get("confidence_after", 1.0)
            if conf_after < conf_before:
                if "deeper_reflection_needed" not in tags:
                    tags.append("deeper_reflection_needed")
                    logger.warning(
                        "confidence_delta_negative",
                        before=conf_before,
                        after=conf_after,
                    )

        elif pattern_type == "multi_agent_interaction":
            conflicts = fields.get("conflict_points", [])
            if conflicts:
                if "coordination_failure" not in tags:
                    tags.append("coordination_failure")
                    logger.warning(
                        "agent_coordination_conflict_detected", conflicts=conflicts
                    )

        return tags

    async def handle_hard_frames(
        self,
        tenant_id: str,
        content: str,
        tags: list[str],
        layer: Optional[str],
        session_id: Optional[str],
        human_label: Optional[str],
        agent_id: Optional[str],
        source: str,
        metadata: Optional[dict],
    ) -> Optional[dict]:
        """SYSTEM 93.1: Hard Frames 2.0 Contract Enforcement helper."""
        import json
        import uuid

        name = human_label or agent_id or source or "Unknown Agent"
        mid = (metadata or {}).get("target_id") or str(uuid.uuid4())

        payload = {}
        if content.strip().startswith("{") and content.strip().endswith("}"):
            try:
                payload = json.loads(content)
            except Exception:
                payload = {"analysis": content}
        else:
            payload = {"analysis": content}

        # Inject actual source content for L1 Grounding verification
        source_memories = await self.service.engine.search_memories(
            query=content, tenant_id=tenant_id, top_k=5
        )
        payload["retrieved_sources_content"] = [m["content"] for m in source_memories]

        payload.update(
            {
                "retrieved_sources": [str(m["id"]) for m in source_memories],
                "decision": (metadata or {}).get("decision", "proceed"),
                "confidence": (metadata or {}).get("confidence", 0.5),
                "metadata": {
                    **(metadata or {}),
                    "trace_id": str(session_id or "audit-000"),
                },
            }
        )

        validation_results = await self.service.reflection_coordinator.run_reflections(payload)

        # Permanent audit trail
        audit_content = (
            f"DECISION AUDIT: {name}\n"
            f"Decision: {payload['decision']}\n"
            f"Confidence: {payload['confidence']}\n"
            f"Reasoning: {payload['analysis'][:500]}\n"
            f"Evidence IDs: {payload['retrieved_sources']}\n"
            f"Validation: {validation_results['final_decision']}"
        )

        await self.service.engine.store_memory(
            tenant_id=tenant_id,
            agent_id="oracle_auditor",
            content=audit_content,
            layer="reflective",
            tags=["decision_provenance", "audit_log"],
            metadata={
                "target_id": mid,
                "evidence_ids": payload["retrieved_sources"],
                "validation_full": validation_results,
            },
        )

        if validation_results.get("final_decision") == "blocked":
            raise ContractViolationError(
                f"Decision Blocked by Oracle: {validation_results['block_reasons']}"
            )

        updated_metadata = (metadata or {}).copy()
        updated_metadata["audit_verified"] = True
        updated_metadata["provenance_link"] = payload["retrieved_sources"]
        return updated_metadata

    def resolve_project_context(self, project: Optional[str]) -> str:
        """Intelligently resolve project name from context."""
        import os

        if project and project != "default":
            return project

        env_project = os.getenv("RAE_PROJECT") or os.getenv("PROJECT_NAME")
        if env_project:
            return env_project

        return "default"

    @staticmethod
    def contains_code(text: str) -> bool:
        """Heuristic check for code presence in memory content."""
        if not text:
            return False
        import re

        code_patterns = [
            r"\bdef\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(",
            r"\bclass\s+[a-zA-Z_][a-zA-Z0-9_]*[\s:\(]",
            r"\bimport\s+[a-zA-Z_]",
            r"\bfrom\s+[a-zA-Z_][a-zA-Z0-9_.]*\s+import",
            r"```[a-zA-Z]*\n",
            r"\bfunction\s+[a-zA-Z_]",
            r"\bconst\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=",
            r"\blet\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=",
            r"\bpublic\s+(?:static\s+)?(?:void|class|function)",
        ]
        return any(re.search(pat, text) for pat in code_patterns)

    async def store_memory(
        self,
        tenant_id: str,
        project: Optional[str],
        content: str,
        source: str,
        importance: Optional[float] = None,
        tags: Optional[list] = None,
        layer: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        ttl: Optional[int] = None,
        info_class: str = "internal",
        governance: Optional[dict] = None,
        metadata: Optional[dict] = None,
        agent_id: Optional[str] = None,
        human_label: Optional[str] = None,
        envelope: Optional[ContextEnvelope] = None,
    ) -> str:
        """Store memory using RAEEngine with security, governance, and audit trails."""
        target_layer = layer or MemoryLayer.EPISODIC
        self.enforce_security_policy(info_class, target_layer, tenant_id=tenant_id)

        tags = tags or []
        if governance:
            tags = self.detect_agentic_patterns(governance, tags)

        if "agent_decision" in tags or "operation_result" in tags or layer == "working":
            try:
                metadata = await self.handle_hard_frames(
                    tenant_id=tenant_id,
                    content=content,
                    tags=tags,
                    layer=layer,
                    session_id=session_id,
                    human_label=human_label,
                    agent_id=agent_id,
                    source=source,
                    metadata=metadata,
                )
            except SecurityPolicyViolationError:
                raise
            except Exception as e:
                logger.warning("audit_failed", error=str(e))

        project_canonical = self.resolve_project_context(project)
        agent_canonical = agent_id or "default"
        metadata = metadata or {}

        from rae_core.ingestion.context_enricher import ContextEnricher

        enricher = ContextEnricher(default_project=project_canonical)
        resolved_envelope = envelope
        if not resolved_envelope and (
            enricher.is_enabled or self.contains_code(content)
        ):
            file_path = metadata.get("file_path") if metadata else None
            resolved_envelope = enricher.build_envelope(
                content=content,
                file_path=file_path,
                project=project_canonical,
                task_id=metadata.get("task_id") if metadata else None,
                trace_id=metadata.get("trace_id") if metadata else None,
            )

        if resolved_envelope:
            if hasattr(resolved_envelope, "model_dump"):
                try:
                    envelope_dict = resolved_envelope.model_dump(mode="json")
                except TypeError:
                    envelope_dict = resolved_envelope.model_dump()
            else:
                envelope_dict = resolved_envelope
            metadata["envelope"] = envelope_dict

        if layer == "sensory" and ttl is None:
            ttl = 86400

        memory_id = await self.service.engine.store_memory(
            tenant_id=tenant_id,
            agent_id=agent_canonical,
            content=content,
            layer=target_layer,
            importance=importance or 0.5,
            tags=tags,
            metadata=metadata,
            human_label=human_label,
            project=project_canonical,
            session_id=session_id,
            memory_type=memory_type or "text",
            ttl=ttl,
            source=source,
            info_class=info_class,
            governance=governance,
            envelope=resolved_envelope,
        )

        # Multimodal Artifact Registration
        if metadata and (
            metadata.get("multimodal")
            or metadata.get("screenshot_url")
            or metadata.get("ocr_text")
            or metadata.get("visual_artifact")
        ):
            try:
                from rae_core.models.multimodal import MultimodalArtifact

                m_info = (
                    metadata.get("multimodal") or metadata.get("visual_artifact") or {}
                )
                if not isinstance(m_info, dict):
                    m_info = {}

                ocr_text = (
                    metadata.get("ocr_text")
                    or m_info.get("ocr_extracted_text")
                    or m_info.get("ocr_text")
                )
                image_uri = (
                    metadata.get("screenshot_url")
                    or m_info.get("image_uri")
                    or f"memory://{memory_id}"
                )
                raw_type = m_info.get("artifact_type") or (
                    "screenshot"
                    if metadata.get("screenshot_url")
                    else "architecture_diagram"
                )

                artifact = MultimodalArtifact(
                    artifact_id=str(m_info.get("artifact_id") or memory_id),
                    artifact_type=raw_type,
                    image_uri=str(image_uri),
                    ocr_extracted_text=ocr_text,
                    visual_embedding=m_info.get("visual_embedding"),
                    text_embedding=m_info.get("text_embedding"),
                    envelope=resolved_envelope,
                )

                if hasattr(self.service.engine, "search_engine") and hasattr(
                    self.service.engine.search_engine, "strategies"
                ):
                    vis_strat = self.service.engine.search_engine.strategies.get("visual")
                    if vis_strat and hasattr(vis_strat, "register_artifact"):
                        vis_strat.register_artifact(UUID(str(memory_id)), artifact)
            except Exception as e:
                logger.warning("failed_to_register_multimodal_artifact", error=str(e))

        logger.info(
            "memory_stored_in_engine",
            memory_id=str(memory_id),
            tenant_id=tenant_id,
            project=project_canonical,
            agent_id=agent_canonical,
            layer=target_layer,
            type=memory_type or "text",
        )

        if self.service.websocket_service:
            try:
                asyncio.create_task(
                    self.service.websocket_service.broadcast_memory_created(
                        tenant_id=tenant_id,
                        project=project_canonical,
                        memory_id=memory_id,
                        content=content,
                        importance=importance or 0.5,
                    )
                )
            except Exception as e:
                logger.warning("websocket_broadcast_failed", error=str(e))

        return str(memory_id)
