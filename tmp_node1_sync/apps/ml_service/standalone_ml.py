from typing import Any, Dict, List, Optional
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import litellm
import os
import uvicorn

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="RAE ML Service (Standalone API-First)",
    description="Machine Learning microservice for RAE - using LiteLLM/Ollama",
    version="2.2.0",
)

class EmbeddingRequest(BaseModel):
    texts: List[str]
    model: str = Field(default="ollama/nomic-embed-text")

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ml-service", "mode": "standalone-api-first"}

@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(req: EmbeddingRequest):
    logger.info("embedding_generation_requested", text_count=len(req.texts), model=req.model)
    try:
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        
        processed_texts = []
        if "nomic" in req.model.lower():
            for t in req.texts:
                processed_texts.append(f"search_document: {t}")
        else:
            processed_texts = req.texts

        response = await litellm.aembedding(
            model=req.model,
            input=processed_texts,
            api_base=api_base
        )
        
        embeddings = [d["embedding"] for d in response["data"]]
        dim = len(embeddings[0]) if embeddings else 0
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model=req.model,
            dimension=dim
        )
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
