"""
Integration test for Semantic Resonance in RAE-Lite.
Verifies if graph-linked memories are boosted during retrieval without an LLM.
"""
import asyncio
import os
from uuid import UUID
from rae_adapters.sqlite import SQLiteStorage, SQLiteGraphStore, SQLiteVectorStore
from rae_core.engine import RAEEngine
from rae_core.interfaces.embedding import IEmbeddingProvider

class TinyEmbedder(IEmbeddingProvider):
    def get_dimension(self) -> int: return 16
    async def embed_text(self, text: str): return [0.1] * 16
    async def embed_batch(self, texts: list[str]): return [[0.1]*16 for _ in texts]

async def test_lite_resonance():
    db_path = "resonance_test.db"
    if os.path.exists(db_path): os.remove(db_path)
    
    storage = SQLiteStorage(db_path)
    graph = SQLiteGraphStore(db_path)
    vector = SQLiteVectorStore(db_path) # Fixed: embedding_dim is dynamic in SQLite adapter
    embedder = TinyEmbedder()

    
    engine = RAEEngine(storage, vector, embedder)
    
    # 1. Store two memories
    id_a = await engine.store_memory("local", "user", "Cooling system failure", layer="episodic")
    id_b = await engine.store_memory("local", "user", "Fluid leakage detected", layer="episodic")
    
    # 2. Link them in the graph (Manually simulating agentic extraction)
    await graph.create_edge(id_a, id_b, "caused_by", "local", weight=1.0)
    
    print("\n--- Phase 1: Search WITHOUT Resonance (simulated via no edges) ---")
    # Resonance happens in RAEEngine.search_memories if get_edges_between returns data
    
    print("--- Phase 2: Search WITH Resonance ---")
    results = await engine.search_memories("cooling problem", "local", top_k=5)
    
    for r in results:
        res_meta = r.get('resonance_metadata', {})
        print(f"Memory: {r['content'][:30]} | Math Score: {r['math_score']:.4f} | Boost: {res_meta.get('boost', 0):.4f}")

    # Validation: Fluid leakage (id_b) should have resonance boost from Cooling system (id_a)
    fluid_mem = next(r for r in results if id_b == r['id'])
    assert fluid_mem.get('resonance_metadata', {}).get('boost', 0) > 0
    print("\n✅ BRILLIANT! Semantic Resonance verified in RAE-Lite mode.")

if __name__ == "__main__":
    asyncio.run(test_lite_resonance())
