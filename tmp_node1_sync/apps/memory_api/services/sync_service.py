from typing import Any, Dict, List

from rae_core.models.sync import SyncLog
from rae_core.sync.manager import SyncManager


class SyncService:
    """Service to handle synchronization operations via API."""

    def __init__(self, sync_manager: SyncManager):
        self.manager = sync_manager

    async def get_sync_topology(self) -> List[Dict[str, Any]]:
        """
        Returns the current topology of connected peers.
        Used for dashboard visualization of the 'Memory Mesh'.
        """
        return [
            {
                "peer_id": p.peer_id,
                "role": p.role,
                "last_seen": p.last_seen,
                "status": "connected",
            }
            for p in self.manager.peers.values()
        ]

    async def get_recent_sync_logs(self, limit: int = 10) -> List[SyncLog]:
        """
        Returns recent sync logs for visualization.
        In a real impl, this would query the DB.
        """
        # Mock data for now as we don't have a SyncLogRepository yet
        return []
