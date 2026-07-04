from fastapi import APIRouter

from apps.memory_api.tasks.background_tasks import rebuild_cache

# Auth is handled globally via FastAPI app dependencies
router = APIRouter(prefix="/cache", tags=["cache"])


@router.post("/rebuild", status_code=202)
async def trigger_rebuild():
    """
    Triggers a background task to rebuild the entire context cache.
    """
    rebuild_cache.delay()
    return {"message": "Cache rebuild task dispatched."}
