from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.tuning_service import TuningService
from rae_core.math.manifold import TheoryAtlas

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Self-Improvement"])


@router.get("/theories")
async def list_available_theories():
    """
    List all mathematical genomes stored in the Theory Atlas.
    These represent historical and modern reasoning strategies.
    """
    atlas = TheoryAtlas()
    return {
        "status": "success",
        "theories": atlas.list_theories(),
        "total_count": len(atlas.list_theories()),
    }


@router.get("/theories/{name}")
async def get_theory_details(name: str):
    """
    Get detailed 'Genome' (mathematical parameters) for a specific theory.
    """
    atlas = TheoryAtlas()
    try:
        arm = atlas.get_arm(name)
        return {
            "status": "success",
            "theory": name,
            "genome": {
                "name": arm.name_alias,
                "alpha": arm.alpha,
                "beta": arm.beta,
                "gamma": arm.gamma,
                "sharpening": arm.sharpening,
                "tier_0_base": arm.tier_0_base,
            },
        }
    except Exception:
        return {"status": "error", "message": f"Theory '{name}' not found in Atlas."}


@router.post("/run")
async def run_tuning(
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
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
        "message": "Bayesian Policy Update started in background.",
    }
