"""Community summarizer for synthesizing reflective memories from graph clusters."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from rae_core.graph.community_detector import GraphCommunity
from rae_core.models.memory import MemoryItem
from rae_core.types.enums import MemoryLayer, MemoryType


class CommunitySynthesis(BaseModel):
    """Synthesized holistic overview of a knowledge graph community."""

    model_config = ConfigDict(extra="forbid")

    community_id: str
    domain: str
    summary: str
    key_entities: list[str] = Field(default_factory=list)
    member_count: int
    synthesized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CommunitySummarizer:
    """
    Synthesizes structural and architectural overviews for graph communities
    and compiles them directly into RAE's Reflective Memory layer.
    """

    def summarize_community(
        self,
        community: GraphCommunity,
        node_contents: dict[UUID, str],
        node_labels: dict[UUID, str] | None = None,
    ) -> CommunitySynthesis:
        """
        Produce deterministic synthesis from community members.
        """
        labels = node_labels or {}
        key_entities = [
            labels[nid] for nid in community.node_ids if nid in labels and labels[nid]
        ]

        # Extract representative topics / symbols from node contents
        snippets = [
            node_contents[nid].strip()
            for nid in community.node_ids
            if nid in node_contents and node_contents[nid].strip()
        ]

        domain = community.domain_label or "architectural_cluster"

        # Deterministic structured synthesis
        overview_lines = [
            f"# Architectural Community Overview: {domain.upper()}",
            f"- Community ID: {community.community_id}",
            f"- Member Nodes: {len(community.node_ids)}",
            f"- Graph Density: {community.density:.2f}",
        ]
        if key_entities:
            overview_lines.append(f"- Key Entities: {', '.join(key_entities[:8])}")

        overview_lines.append("\n## Core Architectural Synthesis:")
        if snippets:
            for i, snip in enumerate(snippets[:5], start=1):
                first_line = snip.split("\n")[0][:120]
                overview_lines.append(f"{i}. {first_line}")
        else:
            overview_lines.append(
                "Connected structural cluster without textual snippets."
            )

        summary = "\n".join(overview_lines)

        return CommunitySynthesis(
            community_id=community.community_id,
            domain=domain,
            summary=summary,
            key_entities=key_entities,
            member_count=len(community.node_ids),
        )

    def to_reflective_memory(
        self,
        synthesis: CommunitySynthesis,
        tenant_id: str,
        agent_id: str = "rae_reflection_engine",
        project: str | None = None,
    ) -> MemoryItem:
        """
        Convert community synthesis into a persisted Reflective MemoryItem.
        """
        return MemoryItem(
            content=synthesis.summary,
            layer=MemoryLayer.REFLECTIVE,
            memory_type=MemoryType.REFLECTION,
            tenant_id=tenant_id,
            agent_id=agent_id,
            project=project or synthesis.domain,
            tags=["graph_community", "reflective_synthesis", synthesis.domain],
            metadata={
                "community_id": synthesis.community_id,
                "domain": synthesis.domain,
                "key_entities": synthesis.key_entities,
                "member_count": synthesis.member_count,
                "synthesized_at": synthesis.synthesized_at.isoformat(),
            },
        )
