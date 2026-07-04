from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from apps.memory_api.models.control_plane import (
    ComputeNode,
    DelegatedTask,
    NodeStatus,
)
from apps.memory_api.repositories.node_repository import NodeRepository
from apps.memory_api.repositories.task_repository import TaskRepository

logger = structlog.get_logger(__name__)


class ControlPlaneService:
    def __init__(self, node_repo: NodeRepository, task_repo: TaskRepository):
        self.node_repo = node_repo
        self.task_repo = task_repo

    async def register_node(
        self, node_id: str, api_key: str, capabilities: dict, ip_address: str
    ) -> ComputeNode:
        # Simple API Key hash for now (in real prod, use proper hashing)
        import hashlib

        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        node = await self.node_repo.register_node(
            node_id, api_key_hash, capabilities, ip_address
        )
        logger.info("node_registered", node_id=node_id, status="ONLINE")
        return node

    async def process_heartbeat(self, node_id: str, status: NodeStatus) -> ComputeNode:
        node = await self.node_repo.update_heartbeat(node_id, status)
        if not node:
            # If heartbeat from unknown node, maybe re-register or fail?
            # For now, fail. Node must register first.
            raise ValueError(f"Node {node_id} not found. Register first.")
        return node

    async def poll_task(self, node_id: str) -> Optional[DelegatedTask]:
        # Resolve node_id string to UUID
        node = await self.node_repo.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found.")

        task = await self.task_repo.claim_task(node.id)
        if task:
            logger.info(
                "task_assigned", task_id=str(task.id), node_id=node_id, type=task.type
            )
        return task

    async def submit_result(
        self, task_id: UUID, result: Dict[str, Any], error: Optional[str] = None
    ) -> DelegatedTask:
        task = await self.task_repo.complete_task(task_id, result, error)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        status = "FAILED" if error else "COMPLETED"
        logger.info("task_completed", task_id=str(task_id), status=status)
        return task

    async def create_task(
        self, type: str, payload: Dict[str, Any], priority: int = 0
    ) -> DelegatedTask:
        task = await self.task_repo.create_task(type, payload, priority)
        logger.info("task_created", task_id=str(task.id), type=type)
        return task

    async def get_task(self, task_id: UUID) -> Optional[DelegatedTask]:
        return await self.task_repo.get_task(task_id)

    async def list_online_nodes(self) -> list[ComputeNode]:
        return await self.node_repo.list_online_nodes()
