"""
RAE ML Service - Microservice for Heavy ML Operations (API-First Version).

This service handles computationally expensive ML operations by delegating them
to specialized providers (like Ollama or OpenAI) via LiteLLM.
"""

import os
from typing import List

import litellm
import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="RAE ML Service",
    description="Machine Learning microservice for RAE - API-First (No local transformers)",
    version="2.2.0",
)

# --- Models ---


class EmbeddingRequest(BaseModel):
    texts: List[str] = Field(..., description="List of texts to embed")
    model: str = Field(
        default="ollama/nomic-embed-text", description="Model name via LiteLLM"
    )


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int


# --- Endpoints ---


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ml-service",
        "mode": "api-first",
        "ollama_base": os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
    }


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(req: EmbeddingRequest):
    logger.info(
        "embedding_generation_requested", text_count=len(req.texts), model=req.model
    )
    try:
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

        # Calibration: Apply Nomic prefixes if using nomic-embed-text
        processed_texts = []
        is_nomic = "nomic" in req.model.lower()
        for t in req.texts:
            if is_nomic and not t.startswith("search_"):
                processed_texts.append(f"search_document: {t}")
            else:
                processed_texts.append(t)

        response = await litellm.aembedding(
            model=req.model,
            input=processed_texts,
            api_base=api_base if "ollama" in req.model.lower() else None,
        )

        embeddings = [d["embedding"] for d in response["data"]]
        dim = len(embeddings[0]) if embeddings else 0

        return EmbeddingResponse(embeddings=embeddings, model=req.model, dimension=dim)
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ML_SERVICE_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec
