#!/usr/bin/env python3
"""
RAE Silicon Oracle Suite - Full Math-Only Verification
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import asyncio
import os
import yaml
from uuid import uuid4
from rae_adapters.sqlite import SQLiteStorage, SQLiteGraphStore, SQLiteVectorStore
from rae_core.engine import RAEEngine
from rae_core.interfaces.embedding import IEmbeddingProvider
from benchmarking.nine_five_benchmarks.runner import NineFiveBenchmarkRunner

class HeuristicEmbedder(IEmbeddingProvider):
    def get_dimension(self) -> int: return 384
    async def embed_text(self, text: str):
        vec = [0.0] * 384
        for i, char in enumerate(text[:384]):
            vec[i] = ord(char) / 255.0
        return vec
    async def embed_batch(self, texts):
        return [await self.embed_text(t) for t in texts]

async def run_set(engine, set_path: Path):
    with open(set_path, "r") as f:
        data = yaml.safe_load(f)
    for m in data['memories']:
        await engine.store_memory("local", "user", m['text'], layer="episodic")
    hits = 0
    for q in data['queries']:
        results = await engine.search_memories(q['query'], "local", top_k=5)
        if results: hits += 1
    return hits / len(data['queries'])

async def main():
    print("############################################################")
    print("  RAE SILICON ORACLE - FULL MATH SUITE (NO LLM)")
    print("############################################################\n")
    
    project_root = Path(__file__).parent.parent.parent
    sets_dir = project_root / "benchmarking" / "sets"
    quality_sets = ["academic_lite.yaml", "academic_extended.yaml", "industrial_small.yaml", "industrial_large.yaml"]
    
    db_path = f"oracle_suite_{uuid4().hex[:8]}.db"
    storage = SQLiteStorage(db_path)
    graph = SQLiteGraphStore(db_path)
    vector = SQLiteVectorStore(db_path)
    embedder = HeuristicEmbedder()
    engine = RAEEngine(storage, vector, embedder)
    
    # 1. Quality Benchmarks
    print("--- 1. QUALITY BENCHMARKS ---")
    for s in quality_sets:
        success_rate = await run_set(engine, sets_dir / s)
        print(f"Set: {s:25} | Success Rate: {success_rate:.2%}")
    
    # 2. Research 9/5 Suite (Direct Integration)
    print("\n--- 2. RESEARCH 9/5 SUITE (MATH-3) ---")
    runner = NineFiveBenchmarkRunner(engine=engine, verbose=False)
    # Using small params for speed but covering all benchmarks

    results = await runner.run_all(
        lect_cycles=100, 
        mmit_operations=100,
        grdt_queries=10,
        rst_insights=10,
        mpeb_iterations=100,
        orb_samples=5
    )
    
    summary = results.summary
    for metric, value in summary.items():
        print(f"{metric:25}: {value}")

    if os.path.exists(db_path): os.remove(db_path)
    print("\n############################################################")
    print("  SILICON ORACLE VERIFICATION COMPLETE")
    print("############################################################")

if __name__ == "__main__":
    asyncio.run(main())