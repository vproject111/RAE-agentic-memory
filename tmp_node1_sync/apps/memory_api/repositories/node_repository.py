import json
from typing import Optional

import asyncpg

from apps.memory_api.models.control_plane import ComputeNode, NodeStatus


class NodeRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def register_node(
        self, node_id: str, api_key_hash: str, capabilities: dict, ip_address: str
    ) -> ComputeNode:
        record = await self.pool.fetchrow(
            """
            INSERT INTO compute_nodes (node_id, api_key_hash, capabilities, ip_address, status, last_heartbeat)
            VALUES ($1, $2, $3, $4, 'ONLINE', NOW())
            ON CONFLICT (node_id)
            DO UPDATE SET
                capabilities = $3,
                ip_address = $4,
                status = 'ONLINE',
                last_heartbeat = NOW(),
                updated_at = NOW()
            RETURNING *
            """,
            node_id,
            api_key_hash,
            json.dumps(capabilities),
            ip_address,
        )
        data = dict(record)
        if isinstance(data.get("capabilities"), str):
            data["capabilities"] = json.loads(data["capabilities"])
        return ComputeNode(**data)

    async def update_heartbeat(
        self, node_id: str, status: NodeStatus
    ) -> Optional[ComputeNode]:
        record = await self.pool.fetchrow(
            """
            UPDATE compute_nodes
            SET last_heartbeat = NOW(), status = $2, updated_at = NOW()
            WHERE node_id = $1
            RETURNING *
            """,
            node_id,
            status.value,
        )
        if record:
            data = dict(record)
            if isinstance(data.get("capabilities"), str):
                data["capabilities"] = json.loads(data["capabilities"])
            return ComputeNode(**data)
        return None

    async def get_node(self, node_id: str) -> Optional[ComputeNode]:
        record = await self.pool.fetchrow(
            "SELECT * FROM compute_nodes WHERE node_id = $1", node_id
        )
        if record:
            data = dict(record)
            if isinstance(data.get("capabilities"), str):
                data["capabilities"] = json.loads(data["capabilities"])
            return ComputeNode(**data)
        return None

    async def list_online_nodes(self) -> list[ComputeNode]:
        """List all nodes that are currently ONLINE and have a recent heartbeat."""
        records = await self.pool.fetch(
            """
            SELECT * FROM compute_nodes
            WHERE status = 'ONLINE'
              AND last_heartbeat > NOW() - INTERVAL '5 minutes'
            """
        )
        nodes = []
        for record in records:
            data = dict(record)
            if isinstance(data.get("capabilities"), str):
                data["capabilities"] = json.loads(data["capabilities"])
            nodes.append(ComputeNode(**data))
        return nodes
