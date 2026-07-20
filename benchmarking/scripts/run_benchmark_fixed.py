# --- START of inlined config.py ---
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB: str = "rae"
    POSTGRES_USER: str = "rae"
    POSTGRES_PASSWORD: str = "rae_password"
    DATABASE_URL: str | None = None
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str | None = None
    RERANKER_API_URL: str = "http://localhost:8001"
    ML_SERVICE_URL: str = "http://localhost:8001"
    MEMORY_API_URL: str = "http://localhost:8000"
    LLM_MODEL: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OLLAMA_API_BASE: str = "http://rae-ollama:11434"
    OLLAMA_API_URL: str = "http://rae-ollama:11434"
    OLLAMA_HOSTS: list[str] = ["http://100.66.252.117:11434", "http://rae-ollama:11434"]
    RAE_LLM_BACKEND: str = "ollama"
    RAE_LLM_MODEL_DEFAULT: str = "ollama/all-minilm"
    RAE_EMBEDDING_MODEL: str | None = None
    EXTRACTION_MODEL: str = "gpt-4o-mini"
    SYNTHESIS_MODEL: str = "gpt-4o"
    RAE_VECTOR_BACKEND: str = "qdrant"
    ONNX_EMBEDDER_PATH: str | None = None
    RAE_USE_GPU: bool = False
    RAE_DB_MODE: str = "migrate"
    RAE_PROFILE: str = "standard"
    OAUTH_ENABLED: bool = True
    OAUTH_DOMAIN: str = ""
    OAUTH_AUDIENCE: str = ""
    TENANCY_ENABLED: bool = True
    DEFAULT_TENANT_ALIAS: str = "default-tenant"
    DEFAULT_TENANT_UUID: str = "00000000-0000-0000-0000-000000000000"
    API_KEY: str = "secret"
    ENABLE_API_KEY_AUTH: bool = False
    ENABLE_JWT_AUTH: bool = False
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ENABLE_RATE_LIMITING: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    ENABLE_COST_TRACKING: bool = False
    ALLOWED_ORIGINS: list[str] = [
        "*",
        "http://localhost:3000",
        "http://localhost:8501",
        "http://localhost:8502",
    ]
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    REDIS_URL: str = "redis://localhost:6379/0"
    MEMORY_RETENTION_DAYS: int = 30
    MEMORY_DECAY_RATE: float = 0.01
    MEMORY_IMPORTANCE_DECAY_ENABLED: bool = True
    MEMORY_IMPORTANCE_DECAY_RATE: float = 0.01
    MEMORY_IMPORTANCE_DECAY_SCHEDULE: str = "0 2 * * *"
    MEMORY_IMPORTANCE_FLOOR: float = 0.01
    MEMORY_IMPORTANCE_ACCELERATED_THRESHOLD_DAYS: int = 30
    MEMORY_IMPORTANCE_PROTECTED_THRESHOLD_DAYS: int = 7
    LOG_LEVEL: str = "WARNING"
    RAE_APP_LOG_LEVEL: str = "INFO"
    OTEL_TRACES_ENABLED: bool = False
    REFLECTIVE_MEMORY_ENABLED: bool = True
    REFLECTIVE_MEMORY_MODE: str = "full"
    REFLECTIVE_MAX_ITEMS_PER_QUERY: int = 5
    REFLECTIVE_LESSONS_TOKEN_BUDGET: int = 1024
    MEMORY_SCORE_WEIGHTS_ALPHA: float = 0.5
    MEMORY_SCORE_WEIGHTS_BETA: float = 0.3
    MEMORY_SCORE_WEIGHTS_GAMMA: float = 0.2
    ENABLE_MATH_V3: bool = True
    MATH_V3_W1_RELEVANCE: float = 0.40
    MATH_V3_W2_IMPORTANCE: float = 0.20
    MATH_V3_W3_RECENCY: float = 0.10
    MATH_V3_W4_CENTRALITY: float = 0.10
    MATH_V3_W5_DIVERSITY: float = 0.10
    MATH_V3_W6_DENSITY: float = 0.10
    ENABLE_SMART_RERANKER: bool = False
    RAE_RERANKER_MODE: str = os.getenv("RAE_RERANKER_MODE", "math")
    RERANKER_MODEL_PATH: str | None = None
    RERANKER_TIMEOUT_MS: int = 10
    RERANKER_TOP_K_CANDIDATES: int = 50
    RERANKER_FINAL_K: int = 10
    ENABLE_FEEDBACK_LOOP: bool = False
    FEEDBACK_POSITIVE_DELTA: float = 0.05
    FEEDBACK_NEGATIVE_DELTA: float = 0.05
    MEMORY_BASE_DECAY_RATE: float = 0.001
    MEMORY_ACCESS_COUNT_BOOST: bool = True
    MEMORY_MIN_DECAY_RATE: float = 0.0001
    MEMORY_MAX_DECAY_RATE: float = 0.01
    REFLECTION_MIN_IMPORTANCE_THRESHOLD: float = 0.3
    REFLECTION_GENERATE_ON_ERRORS: bool = True
    REFLECTION_GENERATE_ON_SUCCESS: bool = False
    DREAMING_ENABLED: bool = False
    DREAMING_LOOKBACK_HOURS: int = 24
    DREAMING_MIN_IMPORTANCE: float = 0.6
    DREAMING_MAX_SAMPLES: int = 20
    SUMMARIZATION_ENABLED: bool = True
    SUMMARIZATION_MIN_EVENTS: int = 10
    SUMMARIZATION_EVENT_THRESHOLD: int = 100
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
# --- END of inlined config.py ---

# --- START of run_benchmark.py ---
import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

import structlog
import yaml

# Add project root and rae-core to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
# sys.path.insert(0, str(PROJECT_ROOT)) # No longer needed for config
sys.path.insert(0, str(PROJECT_ROOT / "rae-core"))

from rae_adapters.postgres import PostgreSQLStorage
from rae_adapters.qdrant import QdrantVectorStore
from rae_core.embedding.native import NativeEmbeddingProvider
from rae_core.engine import RAEEngine
from rae_core.search.engine import HybridSearchEngine
from rae_core.search.strategies.fulltext import FullTextStrategy
from rae_core.search.strategies.vector import VectorSearchStrategy

logger = structlog.get_logger(__name__)


class RAEBenchmarkRunner:
    def __init__(self, dataset_path, tenant_id, queries=100):
        self.dataset_path = Path(dataset_path)
        self.tenant_id = tenant_id
        self.queries = queries
        self.engine = None
        self.pool = None
        self.agent_id = self.dataset_path.stem

    async def setup(self):
        import asyncpg
        from qdrant_client import AsyncQdrantClient

        db_url = os.getenv(
            "DATABASE_URL", "postgresql://rae:rae_password@localhost/rae"
        )
        self.pool = await asyncpg.create_pool(db_url.replace("+asyncpg", ""))

        q_client = AsyncQdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"), port=6333
        )

        storage = PostgreSQLStorage(pool=self.pool)

        model_path = os.path.join(os.getcwd(), "models/all-MiniLM-L6-v2/model.onnx")
        tokenizer_path = os.path.join(
            os.getcwd(), "models/all-MiniLM-L6-v2/tokenizer.json"
        )
        embedding = NativeEmbeddingProvider(
            model_path=model_path, tokenizer_path=tokenizer_path
        )

        vector_store = QdrantVectorStore(
            client=q_client,
            embedding_dim=embedding.get_dimension(),
            vector_name="dense",
        )

        strategies = {
            "vector": VectorSearchStrategy(
                vector_store=vector_store, embedding_provider=embedding
            ),
            "fulltext": FullTextStrategy(memory_storage=storage),
        }

        search_engine = HybridSearchEngine(
            strategies=strategies, embedding_provider=embedding, memory_storage=storage
        )

        self.engine = RAEEngine(
            memory_storage=storage,
            vector_store=vector_store,
            embedding_provider=embedding,
            llm_provider=None,
            settings=Settings(),
            search_engine=search_engine,
        )

        print(f"🚀 Silicon Oracle 300.9 (Turbo Batch) | Project: {self.agent_id}")

    async def run(self, no_wipe: bool = False):
        with open(self.dataset_path, "r") as f:
            data = yaml.safe_load(f)

        if not no_wipe:
            print("🧹 Wiping persistent data for fresh run...")
            async with self.pool.acquire() as conn:
                await conn.execute("TRUNCATE memories CASCADE;")

            print(f"📥 Ingesting {len(data['memories'])} memories (Batching 500)...")
            batch_size = 500
            for i in range(0, len(data["memories"]), batch_size):
                batch = data["memories"][i : i + batch_size]
                tasks = []
                for mem in batch:
                    content = mem.get("text") or mem.get("content", "")
                    nonce = mem.get("metadata", {}).get("nonce", "")
                    tasks.append(
                        self.engine.store_memory(
                            content=content,
                            tenant_id=self.tenant_id,
                            agent_id=self.agent_id,
                            metadata={
                                **mem.get("metadata", {}),
                                "id": mem["id"],
                                "anchor": nonce,
                            },
                            layer=mem.get("layer", "episodic"),
                        )
                    )
                await asyncio.gather(*tasks)
                if i % 5000 == 0:
                    print(f"   Stored {i}/{len(data['memories'])}")
        else:
            print("♻️  Using persistent data in DB (Skipping Ingest)...")

        print(f"🔍 Testing {min(self.queries, len(data['queries']))} queries...")
        total_rr = 0.0
        results_count = 0

        for i, q in enumerate(data["queries"][: self.queries], 1):
            raw_results = await self.engine.search_memories(
                q["query"],
                tenant_id=self.tenant_id,
                agent_id=self.agent_id,
                top_k=300,
                enable_reranking=args_rerank,
            )

            db_ids = [
                UUID(str(r["id"])) if isinstance(r, dict) else UUID(str(r[0]))
                for r in raw_results
            ]
            mapped_ids = []
            if db_ids:
                full = await self.pool.fetch(
                    """
                    SELECT id, 
                           COALESCE(metadata->>'id', metadata->>'external_id', metadata->>'parent_id') as orig 
                    FROM memories 
                    WHERE id = ANY($1)
                """,
                    db_ids,
                )
                mapping = {str(m["id"]): str(m["orig"]) for m in full if m["orig"]}
                mapped_ids = [mapping.get(str(uid), str(uid)) for uid in db_ids]

            rank = 0
            for idx, rid in enumerate(mapped_ids, 1):
                target_ids = [
                    str(sid) for qid in q["expected_source_ids"] for sid in [qid]
                ]
                if str(rid) in target_ids:
                    rank = idx
                    total_rr += 1.0 / rank
                    break

            if rank != 1 and raw_results:
                top_hit = raw_results[0]
                top_id = mapped_ids[0] if mapped_ids else "unknown"
                top_content = top_hit.get("content", "N/A")[:100]
                top_audit = top_hit.get("audit_trail", {})
                logger.info(
                    "rank_1_diagnostic",
                    query=q["query"],
                    top_hit_id=top_id,
                    top_content=top_content,
                    top_audit=top_audit,
                    expected=q["expected_source_ids"][:3],
                )

            results_count += 1
            if i % 10 == 0:
                print(f"   ✅ Q{i} | Rank: {rank if rank > 0 else 'MISS'}")

        final_mrr = total_rr / results_count if results_count > 0 else 0
        print(
            f"========================================\nMRR: {final_mrr:.4f}\n========================================"
        )


async def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--set", type=Path, required=True)
    parser.add_argument("--queries", type=int, default=50)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--no-wipe", action="store_true")

    args, unknown = parser.parse_known_args()

    suite_tenant = "00000000-0000-0000-0000-000000000000"
    print(f"🛡️ Suite Isolation Active | Tenant: {suite_tenant}")

    runner = RAEBenchmarkRunner(args.set, suite_tenant, queries=args.queries)
    try:
        await runner.setup()
        global args_rerank
        args_rerank = args.rerank
        await runner.run(no_wipe=args.no_wipe)
    finally:
        if runner.pool:
            await runner.pool.close()


if __name__ == "__main__":
    asyncio.run(main())
