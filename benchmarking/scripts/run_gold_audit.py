"""
RAE Gold Audit Runner.
Evaluates retrieval quality on pre-loaded data in the database.
Calculates MRR based on 'external_id' lineage.
"""

import asyncio
import os
import sys
from pathlib import Path

import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "rae-core"))

from rae_adapters.postgres import PostgreSQLStorage
from rae_adapters.qdrant import QdrantVectorStore
from rae_core.embedding.native import NativeEmbeddingProvider
from rae_core.engine import RAEEngine


async def run_audit(benchmark_file: str):
    db_url = os.getenv("DATABASE_URL", "postgresql://rae:rae_password@postgres/rae")
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
    qdrant_url = f"http://{qdrant_host}:6333"

    with open(benchmark_file, "r") as f:
        data = yaml.safe_load(f)

    # Setup Engine
    model_dir = "/app/models/all-MiniLM-L6-v2"
    embedding_provider = NativeEmbeddingProvider(
        model_path=f"{model_dir}/model.onnx",
        tokenizer_path=f"{model_dir}/tokenizer.json",
    )
    storage = PostgreSQLStorage(db_url)
    vector_store = QdrantVectorStore(url=qdrant_url)
    engine = RAEEngine(
        memory_storage=storage,
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )

    print(f"🧐 Auditing retrieval quality for {len(data['queries'])} queries...")

    tenant_id = "00000000-0000-0000-0000-000000000000"
    agent_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"

    rr_scores = []
    hits = 0

    for i, q in enumerate(data["queries"]):
        query = q["query"]
        expected_doc_id = q["expected_source_ids"][0]

        results = await engine.search_memories(
            query=query, tenant_id=tenant_id, agent_id=agent_id, limit=10
        )

        rank = 0
        found = False
        for idx, res in enumerate(results):
            try:
                if not isinstance(res, dict):
                    print(f"❌ DATA CORRUPTION: Result {idx} is {type(res)}: {res}")
                    continue

                meta = res.get("metadata")
                if not isinstance(meta, dict):
                    print(
                        f"❌ METADATA CORRUPTION: Result {idx} metadata is {type(meta)}"
                    )
                    actual_ext_id = None
                else:
                    actual_ext_id = meta.get("external_id")
            except Exception as e:
                print(f"💥 CRITICAL ERROR processing result {idx}: {e}")
                continue

            if actual_ext_id == expected_doc_id:
                rank = idx + 1
                rr_scores.append(1.0 / rank)
                found = True
                hits += 1
                break

        if not found:
            rr_scores.append(0.0)

        if (i + 1) % 20 == 0:
            current_mrr = sum(rr_scores) / len(rr_scores)
            print(
                f"  Progress: {i+1}/{len(data['queries'])} | Current MRR: {current_mrr:.4f}"
            )

    mrr = sum(rr_scores) / len(rr_scores)
    hit_rate = (hits / len(data["queries"])) * 100

    print("\n" + "=" * 40)
    print(f"🏆 AUDIT RESULTS: {data['name']}")
    print(f"  MRR:      {mrr:.4f}")
    print(f"  Hit Rate: {hit_rate:.2f}%")
    print("=" * 40)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True)
    args = parser.parse_args()
    asyncio.run(run_audit(args.file))
