from typing import Any, List, Set
from uuid import UUID

import structlog
from qdrant_client.http import models

from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class ConsistencyService:
    """
    Service for ensuring data integrity across distributed stores (Postgres <-> Qdrant).
    """

    def __init__(self, rae_service: RAECoreService):
        self.rae_service = rae_service
        self.db = rae_service.db

    async def reconcile_vectors(
        self, tenant_id: str, collection_name: str = "memories", batch_size: int = 100
    ) -> int:
        """
        Scan Qdrant vectors and remove any that do not exist in Postgres.

        Args:
            tenant_id: Tenant to scan.
            collection_name: Qdrant collection name.
            batch_size: Number of points to verify at once.

        Returns:
            Count of orphaned vectors removed.
        """
        client = self.rae_service.qdrant_client
        if client is None:
            logger.error("reconciliation_skipped_no_qdrant")
            return 0

        logger.info(
            "reconciliation_start", tenant_id=tenant_id, collection=collection_name
        )

        orphans_removed = 0
        offset: Any = None

        try:
            # We iterate using scroll, filtering by tenant_id
            while True:
                scroll_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="tenant_id", match=models.MatchValue(value=tenant_id)
                        )
                    ]
                )

                # Fetch a batch of points from Qdrant
                points, next_offset = await client.scroll(
                    collection_name=collection_name,
                    scroll_filter=scroll_filter,
                    limit=batch_size,
                    offset=offset,
                    with_payload=False,  # We only need IDs
                    with_vectors=False,
                )

                if not points:
                    break

                qdrant_ids = [str(p.id) for p in points]

                # Verify existence in Postgres
                valid_ids = await self._check_existence_in_postgres(
                    qdrant_ids, tenant_id
                )

                # Identify orphans
                orphans = set(qdrant_ids) - valid_ids

                if orphans:
                    logger.warning(
                        "orphans_detected", count=len(orphans), ids=list(orphans)[:5]
                    )

                    # Delete orphans from Qdrant
                    await client.delete(
                        collection_name=collection_name,
                        points_selector=models.PointIdsList(
                            points=[str(oid) for oid in orphans]
                        ),
                    )
                    orphans_removed += len(orphans)

                offset = next_offset
                if offset is None:
                    break

            logger.info(
                "reconciliation_complete", tenant_id=tenant_id, removed=orphans_removed
            )
            return orphans_removed

        except Exception as e:
            logger.error("reconciliation_failed", error=str(e))
            raise

    async def _check_existence_in_postgres(
        self, ids: List[str], tenant_id: str
    ) -> Set[str]:
        """Check which IDs exist in Postgres."""
        if not ids:
            return set()

        # Validate UUIDs to prevent SQL errors if Qdrant has non-UUID ids (legacy)
        uuid_ids = [uid for uid in ids if self._is_uuid(uid)]

        if not uuid_ids:
            return set()

        query = """
            SELECT id::text FROM memories
            WHERE tenant_id = $1 AND id = ANY($2::uuid[])
        """

        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, tenant_id, uuid_ids)

        return {r["id"] for r in rows}

    def _is_uuid(self, val: str) -> bool:
        try:
            UUID(val)
            return True
        except ValueError:
            return False
