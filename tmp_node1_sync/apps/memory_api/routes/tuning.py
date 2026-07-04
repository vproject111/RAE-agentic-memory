from fastapi import APIRouter, Depends, BackgroundTasks
from uuid import UUID
import structlog
from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.tuning_service import TuningService
from apps.memory_api.security.dependencies import get_and_verify_tenant_id

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/tuning", tags=["Self-Improvement"])

@router.post("/run")
async def run_tuning(
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service)
):
    """
    Trigger a Bayesian tuning cycle for current tenant scoring weights.
    Runs in background to ensure API responsiveness.
    """
    service = TuningService(rae_service)
    
    # We run it in background because it's a heavy math operation
    background_tasks.add_task(service.tune_tenant_weights, str(tenant_id))
    
    return {
        "status": "tuning_initiated",
        "message": "Bayesian Policy Update started in background."
    }
