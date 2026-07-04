"""
Repository for A/B Test and Benchmark evaluation data access.

Provides database operations for:
- A/B test definitions and results
- Benchmark suite definitions and executions
- Statistical analysis and comparison
"""

from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from asyncpg import Pool


class ABTestRepository:
    """Repository for A/B test operations."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def create_test(
        self,
        tenant_id: str,
        project_id: str,
        test_name: str,
        variant_a_config: Dict[str, Any],
        variant_b_config: Dict[str, Any],
        primary_metric: str,
        created_by: str,
        description: Optional[str] = None,
        hypothesis: Optional[str] = None,
        variant_a_name: str = "control",
        variant_b_name: str = "treatment",
        traffic_split: float = 0.5,
        min_sample_size: int = 100,
        confidence_level: float = 0.95,
        secondary_metrics: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new A/B test definition."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO ab_tests (
                    tenant_id, project_id, test_name, description, hypothesis,
                    variant_a_name, variant_a_config, variant_b_name, variant_b_config,
                    traffic_split, min_sample_size, confidence_level,
                    primary_metric, secondary_metrics, created_by, tags, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                RETURNING *
                """,
                tenant_id,
                project_id,
                test_name,
                description,
                hypothesis,
                variant_a_name,
                variant_a_config,
                variant_b_name,
                variant_b_config,
                traffic_split,
                min_sample_size,
                confidence_level,
                primary_metric,
                secondary_metrics or [],
                created_by,
                tags or [],
                metadata or {},
            )
        return dict(record)

    async def get_test(self, test_id: UUID) -> Optional[Dict[str, Any]]:
        """Get A/B test by ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM ab_tests WHERE id = $1", test_id
            )
        return dict(record) if record else None

    async def list_tests(
        self,
        tenant_id: str,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List A/B tests for a tenant/project."""
        async with self.pool.acquire() as conn:
            if status:
                records = await conn.fetch(
                    """
                    SELECT * FROM ab_tests
                    WHERE tenant_id = $1 AND project_id = $2 AND status = $3
                    ORDER BY created_at DESC
                    LIMIT $4 OFFSET $5
                    """,
                    tenant_id,
                    project_id,
                    status,
                    limit,
                    offset,
                )
            else:
                records = await conn.fetch(
                    """
                    SELECT * FROM ab_tests
                    WHERE tenant_id = $1 AND project_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    tenant_id,
                    project_id,
                    limit,
                    offset,
                )
        return [dict(r) for r in records]

    async def update_test_status(
        self,
        test_id: UUID,
        status: str,
        winner: Optional[str] = None,
        confidence_score: Optional[float] = None,
        effect_size: Optional[float] = None,
        results_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update A/B test status and results."""
        async with self.pool.acquire() as conn:
            update_fields = ["status = $2"]
            params = [test_id, status]
            param_idx = 3

            if status == "running" and not winner:
                update_fields.append("started_at = NOW()")
            elif status == "completed":
                update_fields.append("completed_at = NOW()")
                if winner:
                    update_fields.append(f"winner = ${param_idx}")
                    params.append(winner)
                    param_idx += 1
                if confidence_score is not None:
                    update_fields.append(f"confidence_score = ${param_idx}")
                    params.append(confidence_score)
                    param_idx += 1
                if effect_size is not None:
                    update_fields.append(f"effect_size = ${param_idx}")
                    params.append(effect_size)
                    param_idx += 1
                if results_summary:
                    update_fields.append(f"results_summary = ${param_idx}")
                    params.append(results_summary)
                    param_idx += 1

                query = f"""
                    UPDATE ab_tests
                    SET {", ".join(update_fields)}
                    WHERE id = $1
                    RETURNING *
                """  # nosec
                record = await conn.fetchrow(query, *params)
            return dict(record)

    async def record_result(
        self,
        test_id: UUID,
        tenant_id: str,
        project_id: str,
        variant: str,
        metric_values: Dict[str, Any],
        query_id: Optional[UUID] = None,
        query_text: Optional[str] = None,
        session_id: Optional[str] = None,
        retrieved_count: Optional[int] = None,
        relevance_labels: Optional[List[int]] = None,
        execution_time_ms: Optional[int] = None,
        user_feedback: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an A/B test observation."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO ab_test_results (
                    test_id, tenant_id, project_id, variant,
                    metric_values, query_id, query_text, session_id,
                    retrieved_count, relevance_labels, execution_time_ms,
                    user_feedback, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
                """,
                test_id,
                tenant_id,
                project_id,
                variant,
                metric_values,
                query_id,
                query_text,
                session_id,
                retrieved_count,
                relevance_labels or [],
                execution_time_ms,
                user_feedback,
                metadata or {},
            )
        return dict(record)

    async def get_test_results(
        self,
        test_id: UUID,
        variant: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get results for an A/B test."""
        async with self.pool.acquire() as conn:
            if variant:
                records = await conn.fetch(
                    """
                    SELECT * FROM ab_test_results
                    WHERE test_id = $1 AND variant = $2
                    ORDER BY recorded_at DESC
                    LIMIT $3
                    """,
                    test_id,
                    variant,
                    limit,
                )
            else:
                records = await conn.fetch(
                    """
                    SELECT * FROM ab_test_results
                    WHERE test_id = $1
                    ORDER BY recorded_at DESC
                    LIMIT $2
                    """,
                    test_id,
                    limit,
                )
        return [dict(r) for r in records]

    async def calculate_statistics(self, test_id: UUID) -> Dict[str, Any]:
        """Calculate statistics for an A/B test using database function."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT calculate_ab_test_statistics($1)", test_id
            )
        return result or {}

    async def delete_test(self, test_id: UUID) -> bool:
        """Delete an A/B test (cascades to results)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM ab_tests WHERE id = $1", test_id)
        return cast(bool, result != "DELETE 0")


class BenchmarkRepository:
    """Repository for benchmark suite operations."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def create_suite(
        self,
        tenant_id: str,
        project_id: str,
        suite_name: str,
        test_queries: List[Dict[str, Any]],
        evaluation_criteria: Dict[str, Any],
        created_by: str,
        description: Optional[str] = None,
        version: str = "1.0",
        expected_results: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300,
        parallel_execution: bool = False,
        retry_on_failure: bool = True,
        is_baseline: bool = False,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new benchmark suite."""
        async with self.pool.acquire() as conn:
            total_queries = len(test_queries)
            record = await conn.fetchrow(
                """
                INSERT INTO benchmark_suites (
                    tenant_id, project_id, suite_name, description, version,
                    test_queries, evaluation_criteria, expected_results,
                    timeout_seconds, parallel_execution, retry_on_failure,
                    is_baseline, total_queries, created_by, tags, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING *
                """,
                tenant_id,
                project_id,
                suite_name,
                description,
                version,
                test_queries,
                evaluation_criteria,
                expected_results,
                timeout_seconds,
                parallel_execution,
                retry_on_failure,
                is_baseline,
                total_queries,
                created_by,
                tags or [],
                metadata or {},
            )
        return dict(record)

    async def get_suite(self, suite_id: UUID) -> Optional[Dict[str, Any]]:
        """Get benchmark suite by ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM benchmark_suites WHERE id = $1", suite_id
            )
        return dict(record) if record else None

    async def list_suites(
        self,
        tenant_id: str,
        project_id: str,
        status: Optional[str] = None,
        is_baseline: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List benchmark suites for a tenant/project."""
        async with self.pool.acquire() as conn:
            conditions = ["tenant_id = $1", "project_id = $2"]
            params: List[Any] = [tenant_id, project_id]
            param_idx = 3

            if status:
                conditions.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1

            if is_baseline is not None:
                conditions.append(f"is_baseline = ${param_idx}")
                params.append(is_baseline)
                param_idx += 1

            params.extend([limit, offset])
            query = f"""
                SELECT * FROM benchmark_suites
                WHERE {" AND ".join(conditions)}
                ORDER BY created_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """  # nosec
            records = await conn.fetch(query, *params)
        return [dict(r) for r in records]

    async def update_suite_status(self, suite_id: UUID, status: str) -> Dict[str, Any]:
        """Update benchmark suite status."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                UPDATE benchmark_suites
                SET status = $2
                WHERE id = $1
                RETURNING *
                """,
                suite_id,
                status,
            )
        return dict(record)

    async def create_execution(
        self,
        suite_id: UUID,
        tenant_id: str,
        project_id: str,
        triggered_by: str = "manual",
        execution_label: Optional[str] = None,
        git_commit_hash: Optional[str] = None,
        config_snapshot: Optional[Dict[str, Any]] = None,
        baseline_execution_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new benchmark execution record."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO benchmark_executions (
                    suite_id, tenant_id, project_id, execution_label,
                    triggered_by, git_commit_hash, config_snapshot,
                    baseline_execution_id, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
                """,
                suite_id,
                tenant_id,
                project_id,
                execution_label,
                triggered_by,
                git_commit_hash,
                config_snapshot,
                baseline_execution_id,
                metadata or {},
            )
        return dict(record)

    async def update_execution(
        self,
        execution_id: UUID,
        status: str,
        queries_executed: Optional[int] = None,
        queries_passed: Optional[int] = None,
        queries_failed: Optional[int] = None,
        overall_score: Optional[float] = None,
        metric_scores: Optional[Dict[str, Any]] = None,
        passed_criteria: Optional[bool] = None,
        total_execution_time_ms: Optional[int] = None,
        avg_query_time_ms: Optional[float] = None,
        improvement_vs_baseline: Optional[float] = None,
        query_results: Optional[List[Dict[str, Any]]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update benchmark execution results."""
        async with self.pool.acquire() as conn:
            update_fields = ["status = $2"]
            params = [execution_id, status]
            param_idx = 3

            if status == "running":
                update_fields.append("started_at = NOW()")
            elif status in ["completed", "failed"]:
                update_fields.append("completed_at = NOW()")

            if queries_executed is not None:
                update_fields.append(f"queries_executed = ${param_idx}")
                params.append(queries_executed)
                param_idx += 1
            if queries_passed is not None:
                update_fields.append(f"queries_passed = ${param_idx}")
                params.append(queries_passed)
                param_idx += 1
            if queries_failed is not None:
                update_fields.append(f"queries_failed = ${param_idx}")
                params.append(queries_failed)
                param_idx += 1
            if overall_score is not None:
                update_fields.append(f"overall_score = ${param_idx}")
                params.append(overall_score)
                param_idx += 1
            if metric_scores is not None:
                update_fields.append(f"metric_scores = ${param_idx}")
                params.append(metric_scores)
                param_idx += 1
            if passed_criteria is not None:
                update_fields.append(f"passed_criteria = ${param_idx}")
                params.append(passed_criteria)
                param_idx += 1
            if total_execution_time_ms is not None:
                update_fields.append(f"total_execution_time_ms = ${param_idx}")
                params.append(total_execution_time_ms)
                param_idx += 1
            if avg_query_time_ms is not None:
                update_fields.append(f"avg_query_time_ms = ${param_idx}")
                params.append(avg_query_time_ms)
                param_idx += 1
            if improvement_vs_baseline is not None:
                update_fields.append(f"improvement_vs_baseline = ${param_idx}")
                params.append(improvement_vs_baseline)
                param_idx += 1
            if query_results is not None:
                update_fields.append(f"query_results = ${param_idx}")
                params.append(query_results)
                param_idx += 1
            if error_message is not None:
                update_fields.append(f"error_message = ${param_idx}")
                params.append(error_message)
                param_idx += 1
            if error_details is not None:
                update_fields.append(f"error_details = ${param_idx}")
                params.append(error_details)
                param_idx += 1

            query = f"""
                UPDATE benchmark_executions
                SET {", ".join(update_fields)}
                WHERE id = $1
                RETURNING *
            """  # nosec
            record = await conn.fetchrow(query, *params)
        return dict(record)

    async def get_execution(self, execution_id: UUID) -> Optional[Dict[str, Any]]:
        """Get benchmark execution by ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM benchmark_executions WHERE id = $1", execution_id
            )
        return dict(record) if record else None

    async def list_executions(
        self,
        suite_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List benchmark executions."""
        async with self.pool.acquire() as conn:
            conditions = []
            params: List[Any] = []
            param_idx = 1

            if suite_id:
                conditions.append(f"suite_id = ${param_idx}")
                params.append(suite_id)
                param_idx += 1
            if tenant_id:
                conditions.append(f"tenant_id = ${param_idx}")
                params.append(tenant_id)
                param_idx += 1
            if project_id:
                conditions.append(f"project_id = ${param_idx}")
                params.append(project_id)
                param_idx += 1
            if status:
                conditions.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.extend([limit, offset])

            query = f"""
                SELECT * FROM benchmark_executions
                {where_clause}
                ORDER BY started_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """  # nosec
            records = await conn.fetch(query, *params)
        return [dict(r) for r in records]

    async def get_baseline_execution(self, suite_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the baseline execution for a suite."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT be.*
                FROM benchmark_executions be
                JOIN benchmark_suites bs ON bs.id = be.suite_id
                WHERE be.suite_id = $1 AND bs.is_baseline = TRUE
                  AND be.status = 'completed'
                ORDER BY be.completed_at DESC
                LIMIT 1
                """,
                suite_id,
            )
        return dict(record) if record else None

    async def delete_suite(self, suite_id: UUID) -> bool:
        """Delete a benchmark suite (cascades to executions)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM benchmark_suites WHERE id = $1", suite_id
            )
        return cast(bool, result != "DELETE 0")
