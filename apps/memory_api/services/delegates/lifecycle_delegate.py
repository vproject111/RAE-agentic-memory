"""Memory lifecycle, maintenance, and tenant administration delegate."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class MemoryLifecycleDelegate:
    """Handles memory maintenance, decay, cleanup, and tenant/project administration."""

    def __init__(self, service: "RAECoreService"):
        self.service = service

    async def delete_memory(self, memory_id: str, tenant_id: str) -> bool:
        """Delete a memory by ID."""
        try:
            mem_uuid = UUID(memory_id)
        except ValueError:
            return False

        return await self.service.postgres_adapter.delete_memory(mem_uuid, tenant_id)

    async def clear_memories(self, tenant_id: str) -> dict:
        """Clear all memories for tenant."""
        return {"deleted": 0}

    async def update_memory_access_batch(
        self,
        memory_ids: List[str],
        tenant_id: str,
    ) -> int:
        """Update access stats for multiple memories."""
        if not memory_ids:
            return 0

        try:
            valid_ids = []
            for mid in memory_ids:
                try:
                    valid_ids.append(UUID(mid))
                except ValueError:
                    continue

            if not valid_ids:
                return 0

            await self.service.postgres_adapter.update_memory_access_batch(
                memory_ids=valid_ids, tenant_id=tenant_id
            )
            return len(valid_ids)
        except Exception as e:
            logger.error("update_memory_access_batch_failed", error=str(e))
            return 0

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        layer: str,
        project: str,
        metric: str,
        func: str,
    ) -> float:
        """Get aggregate metric (e.g., avg importance)."""
        return await self.service.postgres_adapter.get_metric_aggregate(
            tenant_id=tenant_id,
            metric=metric,
            func=func,
            filters={"agent_id": project, "layer": layer},
        )

    async def adjust_importance(
        self,
        memory_id: str | UUID,
        delta: float,
        tenant_id: str,
    ) -> Optional[float]:
        """Adjust memory importance."""
        try:
            if isinstance(memory_id, UUID):
                mem_uuid = memory_id
            else:
                mem_uuid = UUID(str(memory_id))

            return await self.service.postgres_adapter.adjust_importance(
                memory_id=mem_uuid, delta=delta, tenant_id=tenant_id
            )
        except (ValueError, Exception) as e:
            logger.error(
                "adjust_importance_failed", memory_id=str(memory_id), error=str(e)
            )
            return None

    async def decay_importance(
        self,
        tenant_id: str,
        decay_rate: float,
        consider_access_stats: bool = False,
    ) -> int:
        """Apply importance decay to all memories for a tenant."""
        return cast(
            int,
            await self.service.engine.memory_storage.decay_importance(
                tenant_id, decay_rate, consider_access_stats
            ),
        )

    async def apply_global_memory_decay(self, decay_rate: float) -> None:
        """Apply decay to all memories strength."""
        await self.service.db.execute(
            "UPDATE memories SET strength = strength * $1", decay_rate
        )

    async def delete_expired_memories(self) -> int:
        """Delete all expired memories in the system."""
        result = await self.service.db.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < NOW()"
        )
        if result and isinstance(result, str) and result.startswith("DELETE"):
            return int(result.split()[-1])
        return 0

    async def delete_old_episodic_memories(self, days: int) -> int:
        """Delete old episodic memories to manage data lifecycle."""
        interval = f"{days} days"
        result = await self.service.db.execute(
            "DELETE FROM memories WHERE layer = 'episodic' AND created_at < NOW() - $1::interval",
            interval,
        )
        if result and isinstance(result, str) and result.startswith("DELETE"):
            return int(result.split()[-1])
        return 0

    async def get_tenant_weights(self, tenant_id: str) -> Optional[Any]:
        """Retrieve custom scoring weights for tenant from config."""
        try:
            sql = "SELECT config FROM tenants WHERE id = $1"
            config_raw = await self.service.db.fetchval(sql, tenant_id)
            if not config_raw:
                return None

            import json

            config = (
                json.loads(config_raw) if isinstance(config_raw, str) else config_raw
            )

            if config and "math_weights" in config:
                from rae_core.math.structure import ScoringWeights

                w = config["math_weights"]
                return ScoringWeights(
                    alpha=float(w.get("alpha", 0.5)),
                    beta=float(w.get("beta", 0.3)),
                    gamma=float(w.get("gamma", 0.2)),
                )

        except Exception as e:
            logger.warning(
                "failed_to_load_tenant_weights", tenant_id=tenant_id, error=str(e)
            )
        return None

    async def list_unique_tenants(self) -> List[str]:
        """List all unique tenant IDs in the system."""
        if hasattr(self.service.postgres_adapter, "list_unique_tenants"):
            return cast(
                List[str],
                await cast(Any, self.service.postgres_adapter).list_unique_tenants(),
            )

        records = await self.service.db.fetch(
            "SELECT DISTINCT tenant_id FROM memories WHERE tenant_id IS NOT NULL"
        )
        return [str(r["tenant_id"]) for r in records]

    async def list_tenants_with_details(self) -> List[Dict[str, str]]:
        """List all tenants with their names."""
        try:
            records = await self.service.db.fetch(
                "SELECT id, name FROM tenants ORDER BY name"
            )
            return [
                {"id": str(r["id"]), "name": r["name"] or "Unnamed"} for r in records
            ]
        except Exception as e:
            logger.warning("failed_to_list_tenant_details", error=str(e))
            ids = await self.list_unique_tenants()
            return [{"id": i, "name": f"Tenant {i[:8]}..."} for i in ids]

    async def update_tenant_name(self, tenant_id: str, name: str) -> bool:
        """Update tenant name."""
        try:
            exists = await self.service.db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM tenants WHERE id = $1)", tenant_id
            )

            if exists:
                await self.service.db.execute(
                    "UPDATE tenants SET name = $1 WHERE id = $2", name, tenant_id
                )
            else:
                await self.service.db.execute(
                    """
                    INSERT INTO tenants (id, name, tier, config)
                    VALUES ($1, $2, 'enterprise', '{}')
                    ON CONFLICT (id) DO UPDATE SET name = $2
                    """,
                    tenant_id,
                    name,
                )
            return True
        except Exception as e:
            logger.error("update_tenant_name_failed", tenant_id=tenant_id, error=str(e))
            return False

    async def rename_project(
        self, tenant_id: str, old_project_id: str, new_project_id: str
    ) -> bool:
        """Rename a project by updating all references in the database."""
        try:
            if not self.service.postgres_pool:
                return False
            async with self.service.postgres_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """
                        UPDATE memories
                        SET project = $1, agent_id = $1
                        WHERE tenant_id = $2 AND (project = $3 OR agent_id = $3)
                        """,
                        new_project_id,
                        tenant_id,
                        old_project_id,
                    )
                    logger.info(
                        "project_renamed",
                        tenant_id=tenant_id,
                        old=old_project_id,
                        new=new_project_id,
                    )
                    return True
        except Exception as e:
            logger.error("rename_project_failed", error=str(e))
            return False

    async def list_unique_projects(self, tenant_id: str) -> List[str]:
        """List all unique project IDs for a tenant."""
        records = await self.service.db.fetch(
            "SELECT DISTINCT agent_id as project FROM memories WHERE tenant_id = $1 AND agent_id IS NOT NULL",
            tenant_id,
        )
        return [str(r["project"]) for r in records]

    async def list_active_project_tenants(
        self, since: datetime
    ) -> List[Dict[str, str]]:
        """List unique (project, tenant_id) pairs with recent activity."""
        records = await self.service.db.fetch(
            """
            SELECT DISTINCT agent_id as project, tenant_id
            FROM memories
            WHERE created_at >= $1 AND agent_id IS NOT NULL
            """,
            since.replace(tzinfo=None),
        )
        return [{"project": r["project"], "tenant_id": r["tenant_id"]} for r in records]

    async def list_long_sessions(
        self, tenant_id: str, project: str, threshold: int
    ) -> List[Dict[str, Any]]:
        """List sessions with event count above threshold."""
        sql = """
            SELECT
                session_id,
                COUNT(*) as event_count
            FROM memories
            WHERE tenant_id = $1
                AND agent_id = $2
                AND layer = 'episodic'
                AND session_id IS NOT NULL
            GROUP BY session_id
            HAVING COUNT(*) >= $3
            ORDER BY COUNT(*) DESC
        """
        records = await self.service.db.fetch(sql, tenant_id, project, threshold)
        return [dict(r) for r in records]

    async def get_statistics(
        self,
        tenant_id: str,
        project: str,
    ) -> dict:
        """Get memory statistics across all layers."""
        return self.service.engine.get_status()

    async def consolidate_memories(
        self,
        tenant_id: str,
        project: str,
    ) -> dict:
        """Trigger memory consolidation."""
        results = await self.service.engine.run_reflection_cycle(
            tenant_id=tenant_id,
            agent_id="default",
            trigger_type="manual",
        )

        logger.info(
            "memories_consolidated",
            tenant_id=tenant_id,
            project=project,
            results=results,
        )

        if self.service.savings_service and results:
            try:
                tokens_saved = results.get("tokens_saved", 0)
                if tokens_saved > 0:
                    await self.service.savings_service.track_savings(
                        tenant_id=tenant_id,
                        project=project,
                        model="gpt-4o",
                        predicted_tokens=tokens_saved,
                        real_tokens=0,
                        savings_type="compression",
                    )
            except Exception as e:
                logger.warning("failed_to_track_consolidation_savings", error=str(e))

        return results

    async def generate_reflections(
        self,
        tenant_id: str,
        project: str,
    ) -> list:
        """Generate reflections from patterns."""
        return []
