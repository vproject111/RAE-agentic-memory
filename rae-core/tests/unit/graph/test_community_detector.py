"""Unit tests for CommunityDetector and CommunitySummarizer (Iteration 7)."""

from __future__ import annotations

from uuid import uuid4

from rae_core.graph.community_detector import CommunityDetector
from rae_core.models.graph import EdgeType, GraphEdge
from rae_core.reflection.community_summarizer import (
    CommunitySummarizer,
    CommunitySynthesis,
)
from rae_core.types.enums import MemoryLayer, MemoryType


def test_community_detector_clustering():
    detector = CommunityDetector()

    # Community 1: Hybrid Search cluster (n1 <-> n2 <-> n3)
    n1, n2, n3 = uuid4(), uuid4(), uuid4()
    # Community 2: Alembic Migrations cluster (n4 <-> n5)
    n4, n5 = uuid4(), uuid4()

    nodes = [n1, n2, n3, n4, n5]
    edges = [
        GraphEdge(
            source_id=n1,
            target_id=n2,
            edge_type=EdgeType.RELATES_TO,
            tenant_id="tenant-1",
        ),
        GraphEdge(
            source_id=n2,
            target_id=n3,
            edge_type=EdgeType.RELATES_TO,
            tenant_id="tenant-1",
        ),
        GraphEdge(
            source_id=n4,
            target_id=n5,
            edge_type=EdgeType.RELATES_TO,
            tenant_id="tenant-1",
        ),
    ]

    properties = {
        n1: {"domain": "search"},
        n2: {"domain": "search"},
        n3: {"domain": "search"},
        n4: {"domain": "migrations"},
        n5: {"domain": "migrations"},
    }

    communities = detector.detect_communities(
        nodes=nodes,
        edges=edges,
        node_properties=properties,
    )

    assert len(communities) == 2
    domains = [c.domain_label for c in communities]
    assert "search" in domains
    assert "migrations" in domains

    search_comm = next(c for c in communities if c.domain_label == "search")
    assert len(search_comm.node_ids) == 3
    assert search_comm.edge_count == 2
    assert search_comm.density > 0.0

    # Dirty state tracking
    dirty_comm_ids = detector.mark_dirty([n1])
    assert len(dirty_comm_ids) == 1
    assert dirty_comm_ids[0] == search_comm.community_id
    assert search_comm.is_dirty is True


def test_community_summarizer_reflective_synthesis():
    summarizer = CommunitySummarizer()

    n1 = uuid4()
    n2 = uuid4()

    detector = CommunityDetector()
    edges = [
        GraphEdge(
            source_id=n1,
            target_id=n2,
            edge_type=EdgeType.SUPPORTS,
            tenant_id="tenant-1",
        )
    ]
    communities = detector.detect_communities(
        nodes=[n1, n2],
        edges=edges,
        node_properties={
            n1: {"domain": "fusion_gateway"},
            n2: {"domain": "fusion_gateway"},
        },
    )
    comm = communities[0]

    node_contents = {
        n1: "class LogicGateway: Fuses multiple strategy score channels.",
        n2: "def calculate_resonance(): Computes mathematical dot resonance.",
    }
    node_labels = {
        n1: "LogicGateway",
        n2: "calculate_resonance",
    }

    synthesis: CommunitySynthesis = summarizer.summarize_community(
        community=comm,
        node_contents=node_contents,
        node_labels=node_labels,
    )

    assert isinstance(synthesis, CommunitySynthesis)
    assert synthesis.member_count == 2
    assert "LogicGateway" in synthesis.key_entities
    assert "calculate_resonance" in synthesis.key_entities
    assert "Architectural Community Overview" in synthesis.summary

    # Verify Reflective Memory conversion
    mem_item = summarizer.to_reflective_memory(
        synthesis=synthesis,
        tenant_id="tenant-1",
    )
    assert mem_item.layer == MemoryLayer.REFLECTIVE
    assert mem_item.memory_type == MemoryType.REFLECTION
    assert "reflective_synthesis" in mem_item.tags
    assert mem_item.metadata["community_id"] == comm.community_id
