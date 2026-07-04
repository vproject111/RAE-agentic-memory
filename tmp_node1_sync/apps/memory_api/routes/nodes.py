from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from apps.memory_api.dependencies import get_db_pool
from apps.memory_api.models.control_plane import (
    ComputeNode,
    CreateTaskRequest,
    DelegatedTask,
    HeartbeatRequest,
    RegisterNodeRequest,
    TaskResultRequest,
)
from apps.memory_api.repositories.node_repository import NodeRepository
from apps.memory_api.repositories.task_repository import TaskRepository
from apps.memory_api.services.control_plane_service import ControlPlaneService

router = APIRouter(prefix="/control", tags=["Control Plane"])


def get_control_plane_service(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> ControlPlaneService:
    node_repo = NodeRepository(pool)
    task_repo = TaskRepository(pool)
    return ControlPlaneService(node_repo, task_repo)


@router.post("/tasks", response_model=DelegatedTask, status_code=201)
async def create_task(
    req: CreateTaskRequest,
    service: ControlPlaneService = Depends(get_control_plane_service),
):
    """
    Create a new task for delegation to a compute node.
    """
    try:
        return await service.create_task(
            type=req.type, payload=req.payload, priority=req.priority
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks_poll", response_model=Optional[DelegatedTask])
async def poll_task(
    node_id: str = Query(
        ..., description="The unique ID of the compute node polling for tasks"
    ),
    service: ControlPlaneService = Depends(get_control_plane_service),
):
    try:
        return await service.poll_task(node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tasks/{task_id}", response_model=DelegatedTask)
async def get_task(
    task_id: UUID,
    service: ControlPlaneService = Depends(get_control_plane_service),
):
    """
    Get task details by ID.
    """
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/result", response_model=DelegatedTask)
async def submit_result(
    task_id: UUID,
    req: TaskResultRequest,
    service: ControlPlaneService = Depends(get_control_plane_service),
):
    try:
        if task_id != req.task_id:
            raise HTTPException(status_code=400, detail="Task ID mismatch")
        return await service.submit_result(task_id, req.result, req.error)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/nodes/register", response_model=ComputeNode)
async def register_node(
    req: RegisterNodeRequest,
    request: Request,
    service: ControlPlaneService = Depends(get_control_plane_service),
):
    """
    Register a new compute node.
    """
    ip_address = req.ip_address or (
        request.client.host if request.client else "unknown"
    )
    return await service.register_node(
        node_id=req.node_id,
        api_key=req.api_key,
        capabilities=req.capabilities,
        ip_address=ip_address,
    )


@router.post("/nodes/heartbeat", response_model=ComputeNode)
async def heartbeat(
    req: HeartbeatRequest,
    service: ControlPlaneService = Depends(get_control_plane_service),
):
    """
    Update compute node heartbeat and status.
    """
    try:
        return await service.process_heartbeat(node_id=req.node_id, status=req.status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/nodes", response_model=list[ComputeNode])
async def list_nodes(
    service: ControlPlaneService = Depends(get_control_plane_service),
):
    """
    List all online compute nodes.
    """
    return await service.list_online_nodes()
