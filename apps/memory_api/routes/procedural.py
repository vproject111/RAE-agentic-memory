from typing import Optional

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.industrial_bridge import ScreenWatcherBridge
from apps.memory_api.services.rae_core_service import RAECoreService

router = APIRouter(prefix="/procedural", tags=["Procedural Oracle"])
logger = structlog.get_logger(__name__)


class QueryRequest(BaseModel):
    query: str
    project: str = "default"
    model: Optional[str] = None
    source: str = "processed_oee"


@router.post("/query")
async def query_procedural(
    request: QueryRequest, rae_service: RAECoreService = Depends(get_rae_core_service)
):
    try:
        bridge = ScreenWatcherBridge()
        model_map = {"local_qwen": "qwen2.5:3b", "local_llama": "llama3:8b"}
        real_ollama_name = model_map.get(request.model, "qwen2.5:3b")

        # CAŁKOWITE RESETOWANIE KONTEKSTU DLA AUDYTU
        # Wymuszamy aby model zapomniał wszystko o 'Widok jest pusty'
        system_prompt = (
            "Jesteś surowym analitykiem. Twoim jedynym zadaniem jest skomentowanie liczb. "
            "Jeśli widzisz rekordy, opisz je krótko. Jeśli ich nie widzisz, powiedz 'Brak danych'. "
            "ZAKAZ powtarzania frazy 'Widok jest pusty' bez powodu."
        )

        # Ustawiamy temperature na 0 aby uzyskać stabilny wynik
        raw_answer = await rae_service.engine.generate_text(
            prompt=request.query, system_prompt=system_prompt, model=real_ollama_name
        )

        return {
            "instruction": raw_answer,
            "debug": {"model": real_ollama_name, "context": "STATELESS_AUDIT"},
        }

    except Exception as e:
        return {"instruction": f"Błąd: {str(e)}", "results": []}
