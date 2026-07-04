"""Tests for Semantic Resonance Engine."""
import pytest
from rae_core.math.resonance import SemanticResonanceEngine

def test_semantic_resonance_boost():
    engine = SemanticResonanceEngine(resonance_factor=0.5)
    
    # Initial results: A is a direct match, B is not (low score)
    initial_results = [
        {"id": "mem_A", "search_score": 0.9, "content": "Direct hit"},
        {"id": "mem_B", "search_score": 0.1, "content": "Hidden context"}
    ]
    
    # Graph: A and B are strongly connected
    graph_edges = [("mem_A", "mem_B", 1.0)]
    
    resonated = engine.compute_resonance(initial_results, graph_edges)
    
    mem_B = next(r for r in resonated if r["id"] == "mem_B")
    
    # B should have a significantly higher math_score now
    assert mem_B["math_score"] > 0.1
    assert "resonance_metadata" in mem_B
    assert mem_B["resonance_metadata"]["boost"] > 0
