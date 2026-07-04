import asyncio
from contextlib import asynccontextmanager

import asyncpg
import structlog
from qdrant_client import AsyncQdrantClient

from apps.memory_api.celery_app import celery_app
from apps.memory_api.config import settings
from apps.memory_api.dependencies import create_redis_client
from apps.memory_api.repositories.graph_repository import GraphRepository
from apps.memory_api.services.community_detection import CommunityDetectionService
from apps.memory_api.services.consistency_service import ConsistencyService
from apps.memory_api.services.context_cache import rebuild_full_cache
from apps.memory_api.services.entity_resolution import EntityResolutionService
from apps.memory_api.services.graph_extraction import GraphExtractionService
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.reflection_engine import ReflectionEngine

logger = structlog.get_logger(__name__)


# --- Helper to create a DB pool for tasks ---
# Celery tasks run in a separate process, so we need to manage the DB pool.
async def get_pool():
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )


@asynccontextmanager
async def rae_context():
    """
    Context manager to manage lifecycle of RAE dependencies in Celery tasks.
    """
    pool = await get_pool()
    # Handle host containing protocol (e.g. http://qdrant:6333)
    qdrant_host = settings.QDRANT_HOST
    if "://" in qdrant_host:
        qdrant = AsyncQdrantClient(url=qdrant_host)
    else:
        qdrant = AsyncQdrantClient(host=qdrant_host, port=settings.QDRANT_PORT)

    redis = await create_redis_client(settings.REDIS_URL)

    rae_service = RAECoreService(
        postgres_pool=pool,
        qdrant_client=qdrant,
        redis_client=redis,
    )

    try:
        yield rae_service
    finally:
        await qdrant.close()
        await redis.aclose()  # type: ignore[attr-defined]
        await pool.close()


@celery_app.task
def generate_reflection_for_project(project: str, tenant_id: str):
    """
    Celery task to generate a reflection for a specific project.
    """

    async def main():
        async with rae_context() as rae_service:
            engine = ReflectionEngine(
                rae_service.postgres_pool, rae_service=rae_service
            )
            await engine.generate_reflection(project, tenant_id)

    asyncio.run(main())


@celery_app.task
def schedule_reflections():
    """
    Periodically finds projects with recent activity and schedules reflection tasks.
    """

    async def main():
        async with rae_context() as rae_service:
            from datetime import datetime, timedelta, timezone

            since = datetime.now(timezone.utc) - timedelta(hours=1)

            # Find unique project/tenant pairs with recent episodic memories
            records = await rae_service.list_active_project_tenants(since=since)

            for record in records:
                generate_reflection_for_project.delay(
                    record["project"], record["tenant_id"]
                )

    asyncio.run(main())


@celery_app.task
def apply_memory_decay():
    """
    Periodically applies decay to memory strength and deletes expired memories.
    """

    async def main():
        async with rae_context() as rae_service:
            # Apply decay
            await rae_service.apply_global_memory_decay(settings.MEMORY_DECAY_RATE)
            # Delete expired memories
            await rae_service.delete_expired_memories()

    asyncio.run(main())


@celery_app.task
def prune_old_memories():
    """
    Periodically deletes old episodic memories to manage data lifecycle.
    DEPRECATED: Use cleanup_expired_data_task instead for ISO 42001 compliance.
    """

    async def main():
        if settings.MEMORY_RETENTION_DAYS <= 0:
            return  # Pruning is disabled

        async with rae_context() as rae_service:
            # We only prune episodic memories, as semantic/reflective are meant to be long-term.
            deleted_count = await rae_service.delete_old_episodic_memories(
                settings.MEMORY_RETENTION_DAYS
            )
            logger.info("pruned_old_memories", count=deleted_count)

    asyncio.run(main())


@celery_app.task(bind=True, max_retries=3)
def cleanup_expired_data_task(self, tenant_id: str | None = None):
    """
    Enterprise-grade data retention cleanup - ISO/IEC 42001 & GDPR compliance

    Automatically cleans up expired data based on per-tenant retention policies:
    - Episodic memories (configurable per tenant)
    - Embeddings (orphaned or expired)
    - Cost logs (financial records retention)
    - Other data classes per policy

    Features:
    - Per-tenant retention policies
    - Audit trail for all deletions
    - Exception handling (protected tags)
    - GDPR data minimization compliance

    Args:
        tenant_id: Optional tenant ID. If None, processes all tenants.

    Returns:
        Dict with cleanup statistics per data class
    """

    from apps.memory_api.services.retention_service import RetentionService

    async def main():
        async with rae_context() as rae_service:
            try:
                service = RetentionService(rae_service.postgres_pool)

                logger.info(
                    "retention_cleanup_started",
                    tenant_id=tenant_id,
                )

                # Run cleanup
                results = await service.cleanup_expired_data(tenant_id=tenant_id)

                total_deleted = sum(results.values())

                logger.info(
                    "retention_cleanup_complete",
                    tenant_id=tenant_id,
                    total_deleted=total_deleted,
                    breakdown=results,
                )

                return {
                    "success": True,
                    "total_deleted": total_deleted,
                    "breakdown": {k.value: v for k, v in results.items()},
                }

            except Exception as e:
                logger.error(
                    "retention_cleanup_failed",
                    tenant_id=tenant_id,
                    error=str(e),
                )
                raise self.retry(exc=e, countdown=300 * (2**self.request.retries))

    return asyncio.run(main())


@celery_app.task(bind=True, max_retries=3)
def gdpr_delete_user_data_task(
    self, tenant_id: str, user_identifier: str, deleted_by: str
):
    """
    GDPR Article 17: Right to erasure ("right to be forgotten")

    Cascade delete all user data across the system:
    - Memories (episodic, semantic, reflective)
    - Semantic nodes and graph triples
    - Embeddings
    - Reflections
    - Cost logs (anonymized, not deleted)

    This operation is irreversible and creates an audit trail.

    Args:
        tenant_id: Tenant ID
        user_identifier: User email, ID, or other identifier
        deleted_by: Who requested deletion (for audit)

    Returns:
        Dict with deletion statistics
    """

    from apps.memory_api.services.retention_service import RetentionService

    async def main():
        async with rae_context() as rae_service:
            try:
                service = RetentionService(rae_service.postgres_pool)

                logger.info(
                    "gdpr_deletion_started",
                    tenant_id=tenant_id,
                    user_identifier=user_identifier,
                    deleted_by=deleted_by,
                )

                # Execute GDPR deletion
                results = await service.delete_user_data(
                    tenant_id=tenant_id,
                    user_identifier=user_identifier,
                    deleted_by=deleted_by,
                )

                total_deleted = sum(
                    v for k, v in results.items() if not k.endswith("_anonymized")
                )
                total_anonymized = sum(
                    v for k, v in results.items() if k.endswith("_anonymized")
                )

                logger.info(
                    "gdpr_deletion_complete",
                    tenant_id=tenant_id,
                    user_identifier=user_identifier,
                    total_deleted=total_deleted,
                    total_anonymized=total_anonymized,
                    breakdown=results,
                )

                return {
                    "success": True,
                    "total_deleted": total_deleted,
                    "total_anonymized": total_anonymized,
                    "breakdown": results,
                }

            except Exception as e:
                logger.error(
                    "gdpr_deletion_failed",
                    tenant_id=tenant_id,
                    user_identifier=user_identifier,
                    error=str(e),
                )
                raise self.retry(exc=e, countdown=60 * (2**self.request.retries))

    return asyncio.run(main())


@celery_app.task
def rebuild_cache():
    """
    Celery task to perform a full rebuild of the context cache.
    """

    asyncio.run(rebuild_full_cache())


@celery_app.task(bind=True, max_retries=3)
def extract_graph_lazy(
    self, memory_ids: list, tenant_id: str, use_mini_model: bool = True
):
    """
    Celery task to extract knowledge graph from memories in background.

    This is the "lazy" extraction mode that saves costs by:
    1. Processing in background (non-blocking)
    2. Using cheaper LLM model (gpt-4o-mini instead of gpt-4)
    3. Batching memories efficiently
    4. Rate limiting to prevent API saturation

    Args:
        memory_ids: List of memory IDs to process
        tenant_id: Tenant UUID
        use_mini_model: Use cheaper model (gpt-4o-mini) for extraction
    """
    import random

    async def main():
        # Rate limiting: Add initial delay to spread out workers and prevent herd behavior
        # This helps avoid hitting API rate limits when multiple tasks start simultaneously
        delay = random.uniform(0.5, 2.0)
        logger.info(
            "extract_graph_lazy_rate_limit_delay", delay=delay, tenant_id=tenant_id
        )
        await asyncio.sleep(delay)
        async with rae_context() as rae_service:
            try:
                # Initialize service with repositories
                graph_repo = GraphRepository(rae_service.postgres_pool)
                service = GraphExtractionService(
                    rae_service=rae_service, graph_repo=graph_repo
                )

                model = "gpt-4o-mini" if use_mini_model else None

                # Extract graph
                result = await service.extract_knowledge_graph(
                    project_id="default",  # Default project for lazy extraction
                    tenant_id=tenant_id,
                    min_confidence=0.7,  # Higher threshold for background processing
                    limit=50,
                    model=model,
                )

                logger.info(
                    "lazy_graph_extraction_complete",
                    tenant_id=tenant_id,
                    memory_count=len(memory_ids),
                    triples_extracted=len(result.triples),
                    entities_found=len(result.extracted_entities),
                )

                return {
                    "success": True,
                    "triples": len(result.triples),
                    "entities": len(result.extracted_entities),
                }

            except Exception as e:
                logger.error(
                    "lazy_graph_extraction_failed",
                    tenant_id=tenant_id,
                    error=str(e),
                    memory_ids=memory_ids,
                )
                # Retry with exponential backoff
                raise self.retry(exc=e, countdown=60 * (2**self.request.retries))

    return asyncio.run(main())


@celery_app.task
def process_graph_extraction_queue():
    """
    Periodically checks for memories waiting for graph extraction.

    Finds memories that:
    - Are episodic (layer='em')
    - Don't have graph data yet
    - Were created recently

    Then schedules them for lazy extraction.
    """

    async def main():
        async with rae_context() as rae_service:
            # Find memories without graph extraction
            records = await rae_service.list_memories_for_graph_extraction(limit=100)

            for record in records:
                tenant_id = record["tenant_id"]
                memory_ids = record["memory_ids"]

                # Schedule lazy extraction
                extract_graph_lazy.delay(
                    memory_ids=memory_ids, tenant_id=tenant_id, use_mini_model=True
                )

                logger.info(
                    "scheduled_lazy_extraction",
                    tenant_id=tenant_id,
                    memory_count=len(memory_ids),
                )

    asyncio.run(main())


@celery_app.task
def run_entity_resolution_task(project_id: str = "default", tenant_id: str = "default"):
    """
    Periodic task for Pillar 1: Entity Resolution.
    Clusters and merges duplicate nodes.
    """

    async def main():
        async with rae_context() as rae_service:
            service = EntityResolutionService(rae_service=rae_service)
            await service.run_clustering_and_merging(project_id, tenant_id)

    asyncio.run(main())


@celery_app.task
def run_community_detection_task(
    project_id: str = "default", tenant_id: str = "default"
):
    """
    Periodic task for Pillar 2: Community Detection & Summarization.
    Generates 'Wisdom' by summarizing clusters.
    """

    async def main():
        async with rae_context() as rae_service:
            service = CommunityDetectionService(rae_service=rae_service)
            await service.run_community_detection_and_summarization(
                project_id, tenant_id
            )

    asyncio.run(main())


@celery_app.task(bind=True, max_retries=3)
def decay_memory_importance_task(self, tenant_id: str | None = None):
    """
    Enterprise-grade periodic task for memory importance decay.

    Applies temporal decay to memory importance scores across all tenants
    or a specific tenant. Uses ImportanceScoringService with sophisticated
    decay logic that considers:
    - Base decay rate for all memories
    - Accelerated decay for stale memories (not accessed > 30 days)
    - Protected decay for recently accessed memories (< 7 days)

    This task should be scheduled to run daily (e.g., at 2 AM) to maintain
    memory importance scores and naturally age memories over time.

    Args:
        tenant_id: Optional tenant ID to process. If None, processes all tenants.

    Returns:
        Dictionary with processing statistics
    """
    from uuid import UUID

    from apps.memory_api.services.importance_scoring import ImportanceScoringService

    async def main():
        async with rae_context() as rae_service:
            try:
                # Initialize scoring service
                scoring_service = ImportanceScoringService(rae_service=rae_service)

                # Get decay configuration from settings
                decay_rate = settings.MEMORY_DECAY_RATE
                logger.info(
                    "decay_task_started",
                    tenant_id=tenant_id,
                    decay_rate=decay_rate,
                )

                total_updated = 0
                tenants_processed = 0
                failed_tenants = []

                if tenant_id:
                    # Process single tenant
                    try:
                        tenant_uuid = UUID(tenant_id)
                        updated = await scoring_service.decay_importance(
                            tenant_id=tenant_uuid,
                            decay_rate=decay_rate,
                            consider_access_stats=True,
                        )
                        total_updated += updated
                        tenants_processed = 1
                        logger.info(
                            "decay_tenant_complete",
                            tenant_id=tenant_id,
                            updated_count=updated,
                        )
                    except Exception as e:
                        logger.error(
                            "decay_tenant_failed", tenant_id=tenant_id, error=str(e)
                        )
                        failed_tenants.append({"tenant_id": tenant_id, "error": str(e)})
                else:
                    # Process all tenants
                    tenant_ids = await rae_service.list_unique_tenants()

                    logger.info(
                        "decay_processing_all_tenants",
                        tenant_count=len(tenant_ids),
                        decay_rate=decay_rate,
                    )

                    for tenant_id_str in tenant_ids:
                        try:
                            # Try to parse as UUID, if fails use as string
                            try:
                                tenant_uuid = UUID(tenant_id_str)
                            except (ValueError, AttributeError):
                                # If not a valid UUID, skip (could log warning)
                                logger.warning(
                                    "invalid_tenant_id_format", tenant_id=tenant_id_str
                                )
                                continue

                            updated = await scoring_service.decay_importance(
                                tenant_id=tenant_uuid,
                                decay_rate=decay_rate,
                                consider_access_stats=True,
                            )
                            total_updated += updated
                            tenants_processed += 1

                            if updated > 0:
                                logger.info(
                                    "decay_tenant_complete",
                                    tenant_id=tenant_id_str,
                                    updated_count=updated,
                                )
                        except Exception as e:
                            logger.error(
                                "decay_tenant_failed",
                                tenant_id=tenant_id_str,
                                error=str(e),
                            )
                            failed_tenants.append(
                                {"tenant_id": tenant_id_str, "error": str(e)}
                            )
                            # Continue processing other tenants

                result = {
                    "success": True,
                    "total_memories_updated": total_updated,
                    "tenants_processed": tenants_processed,
                    "failed_tenants": failed_tenants,
                    "decay_rate": decay_rate,
                }

                logger.info(
                    "decay_task_complete",
                    total_updated=total_updated,
                    tenants_processed=tenants_processed,
                    failed_count=len(failed_tenants),
                )

                return result

            except Exception as e:
                logger.error("decay_task_fatal_error", error=str(e))
                # Retry with exponential backoff
                raise self.retry(exc=e, countdown=300 * (2**self.request.retries))

    return asyncio.run(main())


@celery_app.task(bind=True, max_retries=3)
def run_maintenance_cycle_task(self):
    """
    Run the complete memory maintenance cycle.

    This task runs the MaintenanceScheduler which coordinates:
    - Decay worker (importance decay)
    - Dreaming worker (background reflections)
    - Summarization worker (session summarization)

    All operations respect configuration flags:
    - REFLECTIVE_MEMORY_ENABLED
    - DREAMING_ENABLED
    - SUMMARIZATION_ENABLED
    - REFLECTIVE_MEMORY_MODE (lite/full)

    Should be scheduled daily (e.g., at 3 AM).
    """

    from apps.memory_api.workers.memory_maintenance import MaintenanceScheduler

    async def main():
        async with rae_context() as rae_service:
            try:
                scheduler = MaintenanceScheduler(rae_service=rae_service)
                stats = await scheduler.run_daily_maintenance()

                logger.info(
                    "maintenance_cycle_complete",
                    decay_updated=stats.get("decay", {}).get("total_updated", 0),
                    dreaming_generated=stats.get("dreaming", {}).get(
                        "reflections_generated", 0
                    ),
                    config=stats.get("config", {}),
                )

                return stats

            except Exception as e:
                logger.error("maintenance_cycle_failed", error=str(e))
                raise self.retry(exc=e, countdown=300 * (2**self.request.retries))

    return asyncio.run(main())


@celery_app.task
def run_dreaming_task(tenant_id: str, project_id: str = "default"):
    """
    Run dreaming cycle for a specific tenant/project.

    Analyzes high-importance memories and generates meta-reflections.
    Only runs if REFLECTIVE_MEMORY_ENABLED and DREAMING_ENABLED are True.
    """

    from apps.memory_api.workers.memory_maintenance import DreamingWorker

    async def main():
        # Check flags before running
        if not settings.REFLECTIVE_MEMORY_ENABLED or not settings.DREAMING_ENABLED:
            logger.info(
                "dreaming_task_skipped",
                tenant_id=tenant_id,
                reason="disabled_by_config",
            )
            return {"skipped": True, "reason": "disabled_by_config"}

        async with rae_context() as rae_service:
            worker = DreamingWorker(rae_service=rae_service)
            results = await worker.run_dreaming_cycle(
                tenant_id=tenant_id,
                project_id=project_id,
                lookback_hours=settings.DREAMING_LOOKBACK_HOURS,
                min_importance=settings.DREAMING_MIN_IMPORTANCE,
                max_samples=settings.DREAMING_MAX_SAMPLES,
            )

            logger.info(
                "dreaming_task_complete",
                tenant_id=tenant_id,
                reflections_generated=len(results),
            )

            return {
                "success": True,
                "reflections_generated": len(results),
                "reflection_ids": results,
            }

    return asyncio.run(main())


@celery_app.task(bind=True, max_retries=3)
def run_consistency_check_task(self, tenant_id: str = "default"):
    """
    Periodic task to fix 'Dual Write' inconsistencies (Ghost Memories).
    Scans Qdrant for orphaned embeddings and removes them.
    """

    async def main():
        async with rae_context() as rae_service:
            try:
                # Use RAECoreService directly
                consistency_service = ConsistencyService(rae_service=rae_service)

                removed = await consistency_service.reconcile_vectors(
                    tenant_id=tenant_id
                )

                logger.info(
                    "consistency_check_task_complete",
                    tenant_id=tenant_id,
                    orphans_removed=removed,
                )
                return {"orphans_removed": removed}
            except Exception as e:
                logger.error("consistency_check_task_failed", error=str(e))
                raise self.retry(exc=e, countdown=300 * (2**self.request.retries))

    return asyncio.run(main())


@celery_app.task(bind=True, max_retries=3)
def run_nightly_quality_audit(self):
    """
    Automated Nocturnal Quality Audit.
    Scans the codebase for recent changes and delegates deep analysis to compute nodes.
    """
    from apps.memory_api.repositories.node_repository import NodeRepository
    from apps.memory_api.repositories.task_repository import TaskRepository
    from apps.memory_api.services.control_plane_service import ControlPlaneService

    async def main():
        async with rae_context() as rae_service:
            try:
                # 1. Check for available nodes
                node_repo = NodeRepository(rae_service.postgres_pool)
                task_repo = TaskRepository(rae_service.postgres_pool)
                service = ControlPlaneService(node_repo, task_repo)

                # Fetch online nodes
                nodes = await node_repo.list_online_nodes()
                if not nodes:
                    logger.info("nightly_audit_skipped", reason="no_online_nodes")
                    return {"skipped": True, "reason": "no_online_nodes"}

                # 2. Get diff for the last 24h (Simple placeholder for now)
                # In real scenario, we'd use git commands if available in the env
                try:
                    import subprocess

                    diff = subprocess.check_output(
                        ["git", "diff", "HEAD@{24hours}..HEAD"],
                        stderr=subprocess.STDOUT,
                    ).decode("utf-8")
                except Exception as e:
                    logger.warning("nightly_audit_git_diff_failed", error=str(e))
                    diff = "Could not fetch git diff. Perform full codebase consistency check instead."

                # 3. Create task
                task = await service.create_task(
                    type="quality_loop",
                    payload={
                        "task": "Perform nocturnal quality audit. Focus on code consistency, agnosticism, and potential logic regressions.",
                        "diff": diff,
                        "writer_model": "deepseek-coder:33b",
                        "reviewer_model": "deepseek-coder:6.7b",
                    },
                    priority=5,  # Lower than interactive tasks
                )

                logger.info("nightly_audit_delegated", task_id=str(task.id))
                return {"success": True, "task_id": str(task.id)}

            except Exception as e:
                logger.error("nightly_audit_failed", error=str(e))
                raise self.retry(exc=e, countdown=600)

    return asyncio.run(main())


@celery_app.task(bind=True, max_retries=3)
def run_bayesian_tuning_task(self, tenant_id: str = "default"):
    """
    Automated Bayesian Weight Tuning.
    Learns optimal weights (alpha, beta, gamma) from user feedback.
    """
    from apps.memory_api.services.tuning_service import TuningService

    async def main():
        async with rae_context() as rae_service:
            try:
                service = TuningService(rae_service)
                result = await service.run_tuning_cycle(tenant_id)
                
                if result.get("posterior"):
                    logger.info(
                        "bayesian_tuning_complete",
                        tenant_id=tenant_id,
                        new_weights=result["posterior"]["new_weights"],
                        confidence=result["posterior"]["confidence"]
                    )
                return result
            except Exception as e:
                logger.error("bayesian_tuning_failed", error=str(e))
                raise self.retry(exc=e, countdown=300)

    return asyncio.run(main())


# --- Celery Beat Schedule ---

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    from celery.schedules import crontab

    # Schedule reflection checks every 5 minutes
    sender.add_periodic_task(
        300.0, schedule_reflections.s(), name="check for reflections every 5 mins"
    )
    # Schedule memory decay every hour (legacy, simple decay)
    sender.add_periodic_task(
        3600.0, apply_memory_decay.s(), name="apply memory decay every hour"
    )
    # Schedule importance decay daily at 2 AM (enterprise-grade decay)
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        decay_memory_importance_task.s(),
        name="decay memory importance daily at 2 AM",
    )
    # Schedule memory pruning once a day (86400 seconds) - DEPRECATED
    sender.add_periodic_task(
        86400.0, prune_old_memories.s(), name="prune old memories daily (deprecated)"
    )
    # Schedule ISO 42001 compliant retention cleanup daily at 1 AM
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        cleanup_expired_data_task.s(),
        name="ISO 42001 retention cleanup daily at 1 AM",
    )
    # Schedule graph extraction queue processing every 10 minutes
    sender.add_periodic_task(
        600.0,
        process_graph_extraction_queue.s(),
        name="process graph extraction queue every 10 mins",
    )
    # Schedule Entity Resolution every hour
    sender.add_periodic_task(
        3600.0, run_entity_resolution_task.s(), name="run entity resolution every hour"
    )
    # Schedule Community Detection every 6 hours
    sender.add_periodic_task(
        21600.0,
        run_community_detection_task.s(),
        name="run community detection every 6 hours",
    )
    # Schedule full maintenance cycle daily at 3 AM (includes dreaming, summarization)
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        run_maintenance_cycle_task.s(),
        name="run full maintenance cycle daily at 3 AM",
    )
    # Schedule Data Consistency Check daily at 4 AM
    sender.add_periodic_task(
        crontab(hour=4, minute=0),
        run_consistency_check_task.s(),
        name="run consistency check daily at 4 AM",
    )
    # Schedule Bayesian Weight Tuning every 10 minutes
    sender.add_periodic_task(
        600.0,
        run_bayesian_tuning_task.s(),
        name="run bayesian weight tuning every 10 mins",
    )

