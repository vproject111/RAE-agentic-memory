from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.rae_core_service import RAECoreService

router = APIRouter(
    prefix="/system",
    tags=["System"],
    dependencies=[Depends(auth.verify_token)],
)


class TenantBasicInfo(BaseModel):
    id: str
    name: str


class TenantUpdate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    name: str


@router.get("/tenants", response_model=List[TenantBasicInfo])
async def list_tenants(
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    List all unique tenant IDs with names.
    """
    return await rae_service.list_tenants_with_details()


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    update: TenantUpdate,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Update tenant name.
    """
    success = await rae_service.update_tenant_name(tenant_id, update.name)
    return {
        "success": success,
        "message": "Tenant updated" if success else "Update failed",
    }


@router.put("/projects/{project_id}")
async def rename_project(
    project_id: str,
    update: ProjectUpdate,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Rename a project (migrate data to new ID).
    """
    success = await rae_service.rename_project(str(tenant_id), project_id, update.name)
    return {
        "success": success,
        "message": "Project renamed" if success else "Rename failed",
    }


@router.get("/projects", response_model=List[str])
async def list_projects(
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    List all unique project IDs for the authenticated tenant.
    """
    return await rae_service.list_unique_projects(tenant_id=str(tenant_id))
