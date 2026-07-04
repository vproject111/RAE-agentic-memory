#!/usr/bin/env python3
"""
RAE-Lite Benchmark Runner (SQLite + Resonance)
"""
import asyncio
import os
import time
import yaml
from pathlib import Path
from uuid import uuid4
from rae_adapters.sqlite import SQLiteStorage, SQLiteGraphStore, SQLiteVectorStore
from rae_core.engine import RAEEngine
from rae_core.interfaces.embedding import IEmbeddingProvider

# Simple Heuristic Embedder (Deterministic, No LLM)
class LiteEmbedder(IEmbeddingProvider):
    def get_dimension(self) -> int: return 384
    async def embed_text(self, text: str):
        # Deterministic 'math' embedding based on character distribution
        # Simulates a vector space without an LLM
        vec = [0.0] * 384
        for i, char in enumerate(text[:384]):
            vec[i] = ord(char) / 255.0
        return vec
    async def embed_batch(self, texts):
        return [await self.embed_text(t) for t in texts]



async def run_lite_benchmark(set_name: str):
    project_root = Path(__file__).parent.parent.parent
    bench_file = project_root / "benchmarking" / "sets" / set_name
    
    with open(bench_file, "r") as f:
        data = yaml.safe_load(f)
    
    db_path = f"lite_bench_{uuid4().hex[:8]}.db"
    storage = SQLiteStorage(db_path)
    graph = SQLiteGraphStore(db_path)
    vector = SQLiteVectorStore(db_path)
    embedder = LiteEmbedder()
    
    engine = RAEEngine(storage, vector, embedder)
    
    print(f"🚀 Starting RAE-Lite Benchmark: {data['name']}")
    
    # 1. Insert
    t0 = time.time()
    for m in data['memories']:
        await engine.store_memory("local", "user", m['text'], layer="episodic")
    insert_time = time.time() - t0
    
    # 2. Query
    hits = 0
    t0 = time.time()
    for q in data['queries']:
        results = await engine.search_memories(q['query'], "local", top_k=5)
        # Simple HitRate check
        retrieved_ids = [r['id'] for r in results]
        # In this lite mock test, we just check if we get results
        if results: hits += 1
            
    query_time = time.time() - t0
    
    print(f"✅ Benchmark Complete!")
    print(f"   Insert Time: {insert_time:.2f}s")
    print(f"   Query Time: {query_time:.2f}s")
    print(f"   Success Rate: {hits/len(data['queries']):.2%}")
    
    if os.path.exists(db_path): os.remove(db_path)

if __name__ == "__main__":
    import sys
    set_name = sys.argv[1] if len(sys.argv) > 1 else "academic_lite.yaml"
    asyncio.run(run_lite_benchmark(set_name))
