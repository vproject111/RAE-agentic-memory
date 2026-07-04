"""
RAE Math - Semantic Resonance Engine

Implements graph-based contextual reinforcement for memory retrieval.
This allows RAE-Lite to achieve 'quasi-reasoning' without an LLM by 
analyzing the connectivity and centrality of retrieved memory manifolds.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from rae_core.math.structure import MemoryScoreResult


class SemanticResonanceEngine:
    """
    Orchestrates contextual reinforcement using memory graph topology.
    Uses 'Resonance Waves' to spread query energy across the memory manifold.
    """
    
    def __init__(self, resonance_factor: float = 0.3):
        self.resonance_factor = resonance_factor

    def compute_resonance(
        self, 
        initial_results: List[Dict[str, Any]], 
        graph_edges: List[Tuple[str, str, float]]
    ) -> List[Dict[str, Any]]:
        """
        Adjust initial scores based on graph connectivity (Semantic Resonance).
        """
        if not initial_results or not graph_edges:
            return initial_results

        # 1. Map memory IDs to scores (ENSURE STRING KEYS for matching)
        id_to_score = {str(r['id']): r.get('search_score', 0.5) for r in initial_results}
        resonance_boosts = {str(r['id']): 0.0 for r in initial_results}

        # 2. Spread energy through edges (Simple PageRank-like push)
        for u, v, weight in graph_edges:
            u_str, v_str = str(u), str(v)
            if u_str in id_to_score and v_str in id_to_score:
                # Mutual reinforcement
                resonance_boosts[u_str] += id_to_score[v_str] * weight * self.resonance_factor
                resonance_boosts[v_str] += id_to_score[u_str] * weight * self.resonance_factor

        # 3. Update results with boosted scores
        for r in initial_results:
            r_id_str = str(r['id'])
            original_score = r.get('math_score') or r.get('search_score', 0.0)
            boost = resonance_boosts.get(r_id_str, 0.0)
            
            # Non-linear combining (soft saturation)
            r['math_score'] = float(original_score + (1.0 - original_score) * np.tanh(boost))
            r['resonance_metadata'] = {
                "boost": float(boost),
                "wave_energy": float(np.tanh(boost))
            }


        # 4. Final sort by the new 'Resonated' score
        initial_results.sort(key=lambda x: x['math_score'], reverse=True)
        return initial_results

    def detect_conceptual_clusters(self, memories: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Groups memories into high-density conceptual manifolds.
        Useful for synthesizing context without an LLM.
        """
        # Placeholder for future spectral clustering logic
        return {"main_cluster": [m['id'] for m in memories]}
