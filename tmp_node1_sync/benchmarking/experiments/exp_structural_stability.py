"""
Experiment 1: Structural Stability Test

Tests how memory structure evolves when adding new memories.

Procedure:
1. Load initial dataset (e.g., industrial_small)
2. Insert all memories
3. Measure: GCS, Entropy, Semantic Coherence
4. Add 20% more memories
5. Re-measure metrics
6. Compare: stability of structure during growth

Expected Results:
- Moderate increase in GCS (better connectivity)
- Low change in entropy (stable organization)
- Increase in semantic coherence (better integration)
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import asyncpg
import numpy as np

from apps.memory_api.services.embedding import get_embedding_service
from benchmarking.math_metrics import (
    GraphConnectivityScore,
    GraphEntropyMetric,
    MemorySnapshot,
    SemanticCoherenceScore,
)


class StructuralStabilityExperiment:
    """Structural stability experiment implementation"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.tenant_id = "exp_structural_stability"
        self.project_id = "exp_project"
        self.pool = None

        # Metrics
        self.gcs_metric = GraphConnectivityScore()
        self.scs_metric = SemanticCoherenceScore()
        self.entropy_metric = GraphEntropyMetric()

    async def setup_database(self):
        """Setup database connection"""
        import os

        db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "rae_memory"),
            "user": os.getenv("POSTGRES_USER", "rae_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "rae_password"),
        }

        self.pool = await asyncpg.create_pool(**db_config, min_size=2, max_size=5)

    async def cleanup_database(self):
        """Cleanup database"""
        if self.pool:
            await self.pool.close()

    async def insert_test_memories(
        self, num_memories: int, prefix: str = "initial"
    ) -> List[str]:
        """Insert test memories and return their IDs"""
        print(f"   Inserting {num_memories} memories ({prefix})...")

        embedding_service = get_embedding_service()
        memory_ids: List[str] = []

        for i in range(num_memories):
            content = f"{prefix} memory {i}: This is test content for structural stability analysis"

            # Generate embedding
            embedding_service.generate_embeddings([content])[0]

            # Insert into database
            assert self.pool is not None
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO memories (
                        tenant_id, content, source, importance,
                        layer, tags, project
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                    """,
                    self.tenant_id,
                    content,
                    "experiment",
                    0.5,
                    "ltm",
                    [prefix],
                    self.project_id,
                )
                memory_ids.append(str(row["id"]))

        return memory_ids

    async def capture_snapshot(self) -> MemorySnapshot:
        """Capture current memory state"""
        # Fetch all memories
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content
                FROM memories
                WHERE tenant_id = $1
                ORDER BY created_at
                """,
                self.tenant_id,
            )

        memory_ids = [str(row["id"]) for row in rows]
        contents = [row["content"] for row in rows]

        # Get embeddings
        embedding_service = get_embedding_service()
        embeddings = embedding_service.generate_embeddings(contents)
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # For this experiment, create synthetic graph edges based on similarity
        # (In real RAE, these would come from the graph service)
        graph_edges = self._create_synthetic_edges(memory_ids, embeddings_array)

        return MemorySnapshot(
            timestamp=datetime.now(),
            memory_ids=memory_ids,
            embeddings=embeddings_array,
            graph_edges=graph_edges,
        )

    def _create_synthetic_edges(
        self, memory_ids: List[str], embeddings: np.ndarray, threshold: float = 0.7
    ) -> List[tuple]:
        """Create synthetic graph edges based on embedding similarity"""
        edges = []

        for i in range(len(memory_ids)):
            for j in range(i + 1, len(memory_ids)):
                # Calculate cosine similarity
                sim = np.dot(embeddings[i], embeddings[j])
                sim /= np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])

                if sim > threshold:
                    edges.append((memory_ids[i], memory_ids[j], float(sim)))

        return edges

    async def run(self) -> Dict[str, Any]:
        """Run the structural stability experiment"""
        print("🔬 Structural Stability Experiment")
        print("Testing memory structure evolution during growth")

        await self.setup_database()

        try:
            # Clean up any existing data
            assert self.pool is not None
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM memories WHERE tenant_id = $1", self.tenant_id
                )

            # Phase 1: Insert initial memories
            print("\n📌 Phase 1: Initial Memory Insertion")
            initial_count = 20
            await self.insert_test_memories(initial_count, prefix="initial")

            snapshot_t0 = await self.capture_snapshot()
            print(f"   ✅ Captured snapshot: {snapshot_t0.num_memories} memories")

            # Calculate initial metrics
            print("\n📊 Calculating initial metrics...")
            gcs_t0 = self.gcs_metric.calculate(
                num_nodes=snapshot_t0.num_memories,
                edges=snapshot_t0.graph_edges,
            )
            entropy_t0 = self.entropy_metric.calculate(
                num_nodes=snapshot_t0.num_memories,
                edges=snapshot_t0.graph_edges,
            )

            scs_t0 = 0.0
            if len(snapshot_t0.graph_edges) > 0:
                scs_t0 = self.scs_metric.calculate(snapshot_t0)

            print(f"   GCS: {gcs_t0:.4f}")
            print(f"   Entropy: {entropy_t0:.4f}")
            print(f"   SCS: {scs_t0:.4f}")

            # Phase 2: Add 20% more memories
            print("\n📌 Phase 2: Adding 20% More Memories")
            additional_count = int(initial_count * 0.2)
            await self.insert_test_memories(additional_count, prefix="additional")

            snapshot_t1 = await self.capture_snapshot()
            print(f"   ✅ Captured snapshot: {snapshot_t1.num_memories} memories")

            # Calculate final metrics
            print("\n📊 Calculating final metrics...")
            gcs_t1 = self.gcs_metric.calculate(
                num_nodes=snapshot_t1.num_memories,
                edges=snapshot_t1.graph_edges,
            )
            entropy_t1 = self.entropy_metric.calculate(
                num_nodes=snapshot_t1.num_memories,
                edges=snapshot_t1.graph_edges,
            )

            scs_t1 = 0.0
            if len(snapshot_t1.graph_edges) > 0:
                scs_t1 = self.scs_metric.calculate(snapshot_t1)

            print(f"   GCS: {gcs_t1:.4f}")
            print(f"   Entropy: {entropy_t1:.4f}")
            print(f"   SCS: {scs_t1:.4f}")

            # Analyze changes
            print("\n📈 Analysis:")
            gcs_change = ((gcs_t1 - gcs_t0) / gcs_t0 * 100) if gcs_t0 > 0 else 0
            entropy_change = (
                ((entropy_t1 - entropy_t0) / entropy_t0 * 100) if entropy_t0 > 0 else 0
            )
            scs_change = ((scs_t1 - scs_t0) / scs_t0 * 100) if scs_t0 > 0 else 0

            print(f"   GCS change: {gcs_change:+.2f}%")
            print(f"   Entropy change: {entropy_change:+.2f}%")
            print(f"   SCS change: {scs_change:+.2f}%")

            # Prepare results
            results = {
                "experiment": "structural_stability",
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "initial_memories": initial_count,
                    "additional_memories": additional_count,
                },
                "phase_1": {
                    "num_memories": snapshot_t0.num_memories,
                    "num_edges": len(snapshot_t0.graph_edges),
                    "gcs": gcs_t0,
                    "entropy": entropy_t0,
                    "scs": scs_t0,
                },
                "phase_2": {
                    "num_memories": snapshot_t1.num_memories,
                    "num_edges": len(snapshot_t1.graph_edges),
                    "gcs": gcs_t1,
                    "entropy": entropy_t1,
                    "scs": scs_t1,
                },
                "analysis": {
                    "gcs_change_percent": gcs_change,
                    "entropy_change_percent": entropy_change,
                    "scs_change_percent": scs_change,
                },
                "conclusion": self._analyze_conclusion(
                    gcs_change, entropy_change, scs_change
                ),
            }

            return results

        finally:
            await self.cleanup_database()

    def _analyze_conclusion(
        self, gcs_change: float, entropy_change: float, scs_change: float
    ) -> str:
        """Generate conclusion based on metric changes"""
        conclusions = []

        if gcs_change > 5:
            conclusions.append("✅ GCS increased moderately - improved connectivity")
        elif gcs_change < -5:
            conclusions.append("⚠️ GCS decreased - degraded connectivity")
        else:
            conclusions.append("✅ GCS stable - maintained connectivity")

        if abs(entropy_change) < 10:
            conclusions.append("✅ Entropy stable - organization maintained")
        else:
            conclusions.append(
                "⚠️ Entropy changed significantly - structure reorganized"
            )

        if scs_change > 0:
            conclusions.append("✅ SCS increased - better semantic integration")
        elif scs_change < -10:
            conclusions.append("⚠️ SCS decreased - weaker semantic links")
        else:
            conclusions.append("✅ SCS stable - maintained coherence")

        return " | ".join(conclusions)
