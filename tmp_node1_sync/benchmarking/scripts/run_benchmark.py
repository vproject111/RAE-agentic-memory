#!/usr/bin/env python3
"""
RAE Benchmark Runner

This script runs benchmarks against the RAE Memory API to evaluate:
- Search quality (MRR, HitRate@k, Precision, Recall)
- Performance (latency, throughput)
- System behavior under different configurations

Usage:
    python run_benchmark.py --set academic_lite.yaml
    python run_benchmark.py --set academic_extended.yaml --output results/
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import asyncpg
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.memory_api.services.embedding import get_embedding_service


class BenchmarkMetrics:
    """Calculate IR evaluation metrics"""

    @staticmethod
    def calculate_mrr(results: List[Tuple[str, List[str]]]) -> float:
        """
        Calculate Mean Reciprocal Rank

        Args:
            results: List of (query_id, [retrieved_doc_ids]) tuples

        Returns:
            MRR score (0.0 to 1.0)
        """
        reciprocal_ranks = []
        for expected_ids, retrieved_ids in results:
            rank = None
            for i, doc_id in enumerate(retrieved_ids, 1):
                if doc_id in expected_ids:
                    rank = i
                    break
            reciprocal_ranks.append(1.0 / rank if rank else 0.0)

        return (
            sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
        )

    @staticmethod
    def calculate_hit_rate(results: List[Tuple[str, List[str]]], k: int = 5) -> float:
        """
        Calculate Hit Rate @ K (% of queries with at least one relevant result in top-k)

        Args:
            results: List of (expected_ids, retrieved_ids) tuples
            k: Number of top results to consider

        Returns:
            Hit rate (0.0 to 1.0)
        """
        hits = 0
        for expected_ids, retrieved_ids in results:
            top_k = retrieved_ids[:k]
            if any(doc_id in expected_ids for doc_id in top_k):
                hits += 1

        return hits / len(results) if results else 0.0

    @staticmethod
    def calculate_precision_at_k(
        results: List[Tuple[List[str], List[str]]], k: int = 5
    ) -> float:
        """
        Calculate average Precision @ K

        Args:
            results: List of (expected_ids, retrieved_ids) tuples
            k: Number of top results to consider

        Returns:
            Average precision (0.0 to 1.0)
        """
        precisions = []
        for expected_ids, retrieved_ids in results:
            top_k = retrieved_ids[:k]
            relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in expected_ids)
            precisions.append(relevant_in_top_k / k if k > 0 else 0.0)

        return sum(precisions) / len(precisions) if precisions else 0.0

    @staticmethod
    def calculate_recall_at_k(
        results: List[Tuple[List[str], List[str]]], k: int = 5
    ) -> float:
        """
        Calculate average Recall @ K

        Args:
            results: List of (expected_ids, retrieved_ids) tuples
            k: Number of top results to consider

        Returns:
            Average recall (0.0 to 1.0)
        """
        recalls = []
        for expected_ids, retrieved_ids in results:
            top_k = retrieved_ids[:k]
            relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in expected_ids)
            recalls.append(
                relevant_in_top_k / len(expected_ids) if expected_ids else 0.0
            )

        return sum(recalls) / len(recalls) if recalls else 0.0


class RAEBenchmarkRunner:
    """Main benchmark runner for RAE Memory API"""

    def __init__(
        self,
        benchmark_file: Path,
        output_dir: Path,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_direct_db: bool = True,
        mock_embeddings: bool = False,
    ):
        self.benchmark_file = benchmark_file
        self.output_dir = output_dir
        self.api_url = api_url or "http://localhost:8000"
        self.api_key = api_key
        self.use_direct_db = use_direct_db
        self.mock_embeddings = mock_embeddings

        self.benchmark_data = None
        self.tenant_id = "00000000-0000-0000-0000-000000000999"
        self.project_id = "benchmark_project"

        # Statistics
        self.insert_times: List[float] = []
        self.query_times: List[float] = []
        self.results: List[Dict[str, Any]] = []

        # Database pool (if using direct DB access)
        self.pool = None

    async def _get_embedding(self, service, texts: List[str]) -> List[List[float]]:
        if self.mock_embeddings:
            # Return dummy 768d vectors (standard for nomic)
            return [[0.1] * 768 for _ in texts]
        return cast(List[List[float]], await service.generate_embeddings_async(texts))

    async def load_benchmark(self):
        """Load benchmark YAML file"""
        print(f"📂 Loading benchmark: {self.benchmark_file.name}")

        with open(self.benchmark_file, "r") as f:
            self.benchmark_data = yaml.safe_load(f)

        if not self.benchmark_data:
            raise ValueError(
                f"Failed to load benchmark data from {self.benchmark_file}"
            )

        # Type assertion for Mypy
        assert isinstance(self.benchmark_data, dict)

        data = self.benchmark_data
        print(f"   Name: {data.get('name', 'Unknown')}")
        print(f"   Description: {data.get('description', 'No description')}")
        print(f"   Memories: {len(data.get('memories', []))}")
        print(f"   Queries: {len(data.get('queries', []))}")

    async def setup_database(self):
        """Setup direct database connection"""
        if not self.use_direct_db:
            return

        print("🔌 Connecting to database...")

        # Get DB credentials from environment or defaults
        import os

        db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "rae_memory"),
            "user": os.getenv("POSTGRES_USER", "rae_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "rae_password"),
        }

        self.pool = await asyncpg.create_pool(**db_config, min_size=2, max_size=5)
        print("   ✅ Database connected")

    async def cleanup_test_data(self):
        """Clean up test data before benchmark"""
        if not self.use_direct_db or not self.pool:
            return

        print("🧹 Cleaning up existing test data...")

        # Lazy import to avoid initialization issues
        from qdrant_client import models
        from qdrant_client.http import models as rest_models

        from apps.memory_api.services.vector_store import get_vector_store

        vector_store = get_vector_store(self.pool)

        # Check collection dimensionality and recreate if necessary
        try:
            # Determine expected dimension from EmbeddingService
            from apps.memory_api.services.embedding import (
                LocalEmbeddingProvider,
                get_embedding_service,
            )

            embedding_service = get_embedding_service()
            # Force initialization to detect model and dimension
            embedding_service._initialize_model()
            provider = LocalEmbeddingProvider(embedding_service)
            expected_dim = provider.get_dimension()
            print(f"   ℹ️ Expected embedding dimension: {expected_dim}")

            collection_info = await vector_store.qdrant_client.get_collection(
                collection_name="memories"
            )

            # Extract size safely
            current_size = None
            vectors_config = collection_info.config.params.vectors

            # Case 1: Single unnamed vector config (VectorParams object)
            if hasattr(vectors_config, "size"):
                current_size = vectors_config.size
            # Case 2: Dictionary of named vectors (common in RAE)
            elif isinstance(vectors_config, dict):
                if "dense" in vectors_config:
                    dense_config = vectors_config["dense"]
                    if hasattr(dense_config, "size"):
                        current_size = dense_config.size
                    elif isinstance(dense_config, dict) and "size" in dense_config:
                        current_size = dense_config["size"]
            # Case 3: Just a dictionary (legacy or other client version)
            elif isinstance(vectors_config, dict) and "size" in vectors_config:
                current_size = vectors_config["size"]

            print(f"   ℹ️ Current collection dimension: {current_size}")

            # Recreate if dimensions mismatch
            if current_size is not None and current_size != expected_dim:
                print(
                    f"   ⚠️ Collection dimension mismatch (found {current_size}, expected {expected_dim}). Recreating with Named Vectors..."
                )
                await vector_store.qdrant_client.delete_collection("memories")
                # Use standard RAE vectors config to maintain model agnosticism
                await vector_store.qdrant_client.create_collection(
                    collection_name="memories",
                    vectors_config={
                        "dense": rest_models.VectorParams(
                            size=expected_dim, distance=rest_models.Distance.COSINE
                        ),
                        "openai": rest_models.VectorParams(
                            size=1536, distance=rest_models.Distance.COSINE
                        ),
                        "ollama": rest_models.VectorParams(
                            size=768, distance=rest_models.Distance.COSINE
                        ),
                    },
                    sparse_vectors_config={"text": models.SparseVectorParams()},
                )
                print(f"   ✅ Collection recreated with Named Vectors (dense={expected_dim}, ollama=768, openai=1536)")
        except Exception as e:
            print(f"   ℹ️ Could not check/recreate collection: {e}")

        # Delete ALL vectors with this tenant_id from Qdrant using filter-based deletion
        # This is more thorough than deleting only vectors that are in PostgreSQL
        print(f"   Deleting all vectors for tenant '{self.tenant_id}' from Qdrant...")
        try:
            await vector_store.qdrant_client.delete(
                collection_name="memories",
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="tenant_id",
                                match=models.MatchValue(value=self.tenant_id),
                            )
                        ]
                    )
                ),
            )
            print("   ✅ Qdrant cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Qdrant cleanup failed: {e}")

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            # Delete from PostgreSQL
            await conn.execute(
                "DELETE FROM memories WHERE tenant_id = $1", self.tenant_id
            )

            # Delete vectors for this tenant (if table exists)
            try:
                await conn.execute(
                    "DELETE FROM memory_vectors WHERE tenant_id = $1", self.tenant_id
                )
            except asyncpg.exceptions.UndefinedTableError:
                # Table doesn't exist, skip cleanup
                pass

        print("   ✅ Cleanup complete")

    async def insert_memories(self):
        """Insert memories into RAE"""
        assert self.benchmark_data is not None
        data = self.benchmark_data
        memories = data["memories"]
        print(f"\n📝 Inserting {len(memories)} memories...")

        # Lazy import to avoid initialization issues in test environments
        from apps.memory_api.services.vector_store import get_vector_store

        embedding_service = get_embedding_service()
        vector_store = get_vector_store(self.pool)

        memories = self.benchmark_data.get("memories", [])
        assert isinstance(memories, list)

        for i, memory in enumerate(memories, 1):
            assert isinstance(memory, dict)
            start_time = time.time()

            try:
                # Generate embedding with explicit document prefix
                content = memory["text"]
                prefixed_content = (
                    f"search_document: {content}"
                    if not content.startswith("search_")
                    else content
                )

                embeddings = await self._get_embedding(
                    embedding_service, [prefixed_content]
                )
                embedding = embeddings[0]

                # Insert into database
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO memories (
                            tenant_id, content, source, importance,
                            layer, tags, project
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id, created_at
                        """,
                        self.tenant_id,
                        content,
                        memory.get("metadata", {}).get("source", "benchmark"),
                        memory.get("metadata", {}).get("importance", 0.5),
                        "semantic",
                        memory.get("tags", []),
                        self.project_id,
                    )

                    memory_id = row["id"]
                    created_at = row["created_at"]

                    # Store memory ID for later reference
                    memory["_db_id"] = memory_id

                    # Insert vector - create MemoryRecord and use batch upsert
                    from apps.memory_api.models import MemoryLayer, MemoryRecord

                    memory_record = MemoryRecord(
                        id=str(memory_id),
                        tenant_id=self.tenant_id,
                        content=content,
                        source=memory.get("metadata", {}).get("source", "benchmark"),
                        importance=memory.get("metadata", {}).get("importance", 0.5),
                        layer=MemoryLayer.semantic,
                        tags=memory.get("tags", []),
                        timestamp=created_at,
                        project=self.project_id,
                    )
                    # Await the async upsert
                    await vector_store.upsert([memory_record], [embedding])

                elapsed = time.time() - start_time
                self.insert_times.append(elapsed)

                if i % 10 == 0:
                    print(
                        f"   ✅ Inserted {i}/{len(self.benchmark_data['memories'])} memories"
                    )

            except Exception as e:
                print(
                    f"   ❌ Error inserting memory {memory.get('id', 'unknown')}: {e}"
                )
                raise

        avg_time = (
            sum(self.insert_times) / len(self.insert_times) if self.insert_times else 0
        )
        print(f"   ⏱️  Average insert time: {avg_time * 1000:.2f}ms")

    async def run_queries(self):
        """Execute all benchmark queries and collect results"""
        assert self.benchmark_data is not None
        data = self.benchmark_data
        print(f"\n🔍 Running {len(data['queries'])} queries...")

        # Lazy import to avoid initialization issues in test environments
        from apps.memory_api.services.vector_store import get_vector_store

        embedding_service = get_embedding_service()
        vector_store = get_vector_store(self.pool)

        config: Dict[str, Any] = data.get("config", {})
        top_k = config.get("top_k", 5)

        queries = data.get("queries", [])
        assert isinstance(queries, list)

        for i, query_data in enumerate(queries, 1):
            assert isinstance(query_data, dict)
            query_text = query_data["query"]
            expected_ids = query_data["expected_source_ids"]

            start_time = time.time()

            try:
                # Generate query embedding with explicit query prefix
                prefixed_query = (
                    f"search_query: {query_text}"
                    if not query_text.startswith("search_")
                    else query_text
                )
                query_embeddings = await self._get_embedding(
                    embedding_service, [prefixed_query]
                )
                query_embedding = query_embeddings[0]

                # Search vectors - use query method with filters
                filters = {
                    "must": [{"key": "tenant_id", "match": {"value": self.tenant_id}}]
                }
                # Await the async query
                search_results = await vector_store.query(
                    query_embedding=query_embedding, top_k=top_k, filters=filters
                )

                elapsed = time.time() - start_time
                self.query_times.append(elapsed)

                # Map DB IDs back to benchmark IDs
                retrieved_ids = []
                memories_list = self.benchmark_data.get("memories", [])
                assert isinstance(memories_list, list)

                for result in search_results:
                    # Find the original benchmark ID
                    for memory in memories_list:
                        assert isinstance(memory, dict)
                        if str(memory.get("_db_id")) == str(result.id):
                            retrieved_ids.append(memory["id"])
                            break

                # Store results for metric calculation
                self.results.append(
                    {
                        "query": query_text,
                        "expected": expected_ids,
                        "retrieved": retrieved_ids,
                        "latency_ms": elapsed * 1000,
                        "difficulty": query_data.get("difficulty", "unknown"),
                        "category": query_data.get("category", "unknown"),
                    }
                )

                if i % 5 == 0:
                    print(
                        f"   ✅ Completed {i}/{len(self.benchmark_data['queries'])} queries"
                    )

            except Exception as e:
                print(f"   ❌ Error running query '{query_text}': {e}")
                raise

        avg_time = (
            sum(self.query_times) / len(self.query_times) if self.query_times else 0
        )
        print(f"   ⏱️  Average query time: {avg_time * 1000:.2f}ms")

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate all benchmark metrics"""
        print("\n📊 Calculating metrics...")

        # Prepare data for metric calculation
        results_tuple = [(r["expected"], r["retrieved"]) for r in self.results]

        # Ensure benchmark data is loaded for config access
        if self.benchmark_data:
            self.benchmark_data.get("config", {})

        k_values = [3, 5, 10]

        metrics: Dict[str, Any] = {
            "mrr": BenchmarkMetrics.calculate_mrr(results_tuple),
            "hit_rate": {},
            "precision": {},
            "recall": {},
        }

        for k in k_values:
            # Cast sub-dictionaries for Mypy
            hit_rate_dict = cast(Dict[str, float], metrics["hit_rate"])
            precision_dict = cast(Dict[str, float], metrics["precision"])
            recall_dict = cast(Dict[str, float], metrics["recall"])

            hit_rate_dict[f"@{k}"] = BenchmarkMetrics.calculate_hit_rate(
                results_tuple, k
            )
            precision_dict[f"@{k}"] = BenchmarkMetrics.calculate_precision_at_k(
                results_tuple, k
            )
            recall_dict[f"@{k}"] = BenchmarkMetrics.calculate_recall_at_k(
                results_tuple, k
            )

        # Performance metrics
        metrics["performance"] = {
            "avg_insert_time_ms": (
                (sum(self.insert_times) / len(self.insert_times) * 1000)
                if self.insert_times
                else 0
            ),
            "avg_query_time_ms": (
                (sum(self.query_times) / len(self.query_times) * 1000)
                if self.query_times
                else 0
            ),
            "p95_query_time_ms": (
                sorted(self.query_times)[int(len(self.query_times) * 0.95)] * 1000
                if self.query_times
                else 0
            ),
            "p99_query_time_ms": (
                sorted(self.query_times)[int(len(self.query_times) * 0.99)] * 1000
                if self.query_times
                else 0
            ),
        }

        # Quality score (weighted average)
        # Cast to typed dicts to avoid "object" errors
        hit_rate = cast(Dict[str, float], metrics["hit_rate"])
        precision = cast(Dict[str, float], metrics["precision"])
        recall = cast(Dict[str, float], metrics["recall"])
        mrr = cast(float, metrics["mrr"])

        metrics["overall_quality_score"] = float(
            mrr * 0.4
            + hit_rate["@5"] * 0.3
            + precision["@5"] * 0.15
            + recall["@5"] * 0.15
        )

        print(f"   MRR: {metrics['mrr']:.4f}")
        print(f"   Hit Rate @5: {metrics['hit_rate']['@5']:.4f}")
        print(f"   Overall Quality: {metrics['overall_quality_score']:.4f}")

        return metrics

    def save_results(self, metrics: Dict[str, Any]):
        """Save benchmark results to JSON and Markdown"""
        assert self.benchmark_data is not None
        assert isinstance(self.benchmark_data, dict)
        data = self.benchmark_data
        print("\n💾 Saving results...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        benchmark_name = data["name"]

        # Prepare results data
        project_root = Path(__file__).parent.parent.parent
        try:
            rel_benchmark_file = self.benchmark_file.relative_to(project_root)
        except ValueError:
            rel_benchmark_file = self.benchmark_file

        results_data = {
            "benchmark": {
                "name": benchmark_name,
                "description": data["description"],
                "version": data.get("version", "1.0"),
                "file": str(rel_benchmark_file),
            },
            "execution": {
                "timestamp": datetime.now().isoformat(),
                "num_memories": len(data["memories"]),
                "num_queries": len(data["queries"]),
                "total_time_seconds": sum(self.insert_times) + sum(self.query_times),
            },
            "metrics": metrics,
            "detailed_results": self.results,
        }

        # Save JSON
        json_file = self.output_dir / f"{benchmark_name}_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(results_data, f, indent=2)
        print(f"   ✅ JSON: {json_file}")

        # Generate Markdown report
        md_file = self.output_dir / f"{benchmark_name}_{timestamp}.md"
        self._generate_markdown_report(md_file, results_data, metrics)
        print(f"   ✅ Report: {md_file}")

    def _generate_markdown_report(
        self, md_file: Path, results_data: Dict, metrics: Dict
    ):
        """Generate human-readable Markdown report"""
        with open(md_file, "w") as f:
            f.write(f"# RAE Benchmark Report: {results_data['benchmark']['name']}\n\n")
            f.write(f"**Description:** {results_data['benchmark']['description']}\n\n")
            f.write(f"**Executed:** {results_data['execution']['timestamp']}\n\n")
            f.write("---\n\n")

            f.write("## Dataset Overview\n\n")
            f.write(f"- **Memories:** {results_data['execution']['num_memories']}\n")
            f.write(f"- **Queries:** {results_data['execution']['num_queries']}\n")
            f.write(
                f"- **Total Time:** {results_data['execution']['total_time_seconds']:.2f}s\n\n"
            )

            f.write("## Quality Metrics\n\n")
            f.write(f"- **MRR:** {metrics['mrr']:.4f}\n")
            f.write(f"- **Hit Rate @3:** {metrics['hit_rate']['@3']:.4f}\n")
            f.write(f"- **Hit Rate @5:** {metrics['hit_rate']['@5']:.4f}\n")
            f.write(f"- **Hit Rate @10:** {metrics['hit_rate']['@10']:.4f}\n")
            f.write(f"- **Precision @5:** {metrics['precision']['@5']:.4f}\n")
            f.write(f"- **Recall @5:** {metrics['recall']['@5']:.4f}\n")
            f.write(
                f"- **Overall Quality Score:** {metrics['overall_quality_score']:.4f}\n\n"
            )

            f.write("## Performance Metrics\n\n")
            perf = metrics["performance"]
            f.write(f"- **Average Insert Time:** {perf['avg_insert_time_ms']:.2f}ms\n")
            f.write(f"- **Average Query Time:** {perf['avg_query_time_ms']:.2f}ms\n")
            f.write(f"- **P95 Query Time:** {perf['p95_query_time_ms']:.2f}ms\n")
            f.write(f"- **P99 Query Time:** {perf['p99_query_time_ms']:.2f}ms\n\n")

            f.write("## Observations\n\n")
            if metrics["mrr"] > 0.7:
                f.write("- ✅ Excellent MRR score - search quality is high\n")
            elif metrics["mrr"] > 0.5:
                f.write("- ⚠️ Good MRR score - room for improvement\n")
            else:
                f.write("- ❌ Low MRR score - search quality needs attention\n")

            if perf["avg_query_time_ms"] < 50:
                f.write("- ✅ Excellent query latency\n")
            elif perf["avg_query_time_ms"] < 100:
                f.write("- ⚠️ Acceptable query latency\n")
            else:
                f.write("- ❌ High query latency - optimization needed\n")

            f.write("\n---\n\n")
            f.write("*Generated by RAE Benchmarking Suite*\n")

    async def cleanup(self):
        """Cleanup resources"""
        if self.pool:
            await self.pool.close()


async def main():
    parser = argparse.ArgumentParser(description="Run RAE benchmarks")
    parser.add_argument(
        "--set",
        type=str,
        required=True,
        help="Benchmark set to run (e.g., academic_lite.yaml)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarking/results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--api-url", type=str, help="RAE API URL (default: direct DB access)"
    )
    parser.add_argument("--api-key", type=str, help="API key for authentication")
    parser.add_argument(
        "--mock", action="store_true", help="Use mock embeddings for speed testing"
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent.parent
    benchmark_file = project_root / "benchmarking" / "sets" / args.set
    output_dir = project_root / args.output

    if not benchmark_file.exists():
        print(f"❌ Benchmark file not found: {benchmark_file}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Run benchmark
    print("🚀 RAE Benchmark Runner")
    print("=" * 60)

    runner = RAEBenchmarkRunner(
        benchmark_file=benchmark_file,
        output_dir=output_dir,
        api_url=args.api_url,
        api_key=args.api_key,
        use_direct_db=True,  # Always use direct DB for benchmarks
        mock_embeddings=args.mock,
    )

    try:
        await runner.load_benchmark()
        await runner.setup_database()
        await runner.cleanup_test_data()
        await runner.insert_memories()
        await runner.run_queries()

        metrics = runner.calculate_metrics()
        runner.save_results(metrics)

        print("\n✅ Benchmark complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
