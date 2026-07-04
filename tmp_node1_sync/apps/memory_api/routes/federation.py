import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.memory_api.models.federation_models import (
    FederationQueryRequest,
    FederationQueryResponse,
    FederationResultItem,
)
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.security import auth
from apps.memory_api.services.hybrid_search_service import HybridSearchService

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(
    prefix="/federation", tags=["Federation"], dependencies=[Depends(auth.verify_token)]
)


async def get_pool(request: Request):
    return request.app.state.pool


@router.post("/query", response_model=FederationQueryResponse)
async def federation_query(
    request: FederationQueryRequest, req: Request, pool=Depends(get_pool)
):
    """
    Federation endpoint to expose memories to other RAE instances.
    Returns candidates without embeddings.

    This endpoint is designed for low-latency retrieval by trusted federation peers.
    """
    with tracer.start_as_current_span("rae.api.federation.query") as span:
        span.set_attribute("rae.tenant_id", request.tenant_id)
        span.set_attribute("rae.project_id", request.project_id)

        logger.info(
            "federation_query_received",
            tenant_id=request.tenant_id,
            query=request.query_text,
        )

        try:
            # Use RAECoreService via app state
            if not hasattr(req.app.state, "rae_core_service"):
                raise HTTPException(
                    status_code=503, detail="RAE Core Service not available"
                )

            rae_service = req.app.state.rae_core_service
            service = HybridSearchService(rae_service)

            # Execute fast hybrid search (no reranking)
            # Federation usually requires low latency, so we skip heavy reranking
            results = await service.search(
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                query=request.query_text,
                k=request.limit,
                enable_reranking=False,
                enable_graph=False,
            )

            fed_results = []
            for res in results.results:
                fed_results.append(
                    FederationResultItem(
                        memory_id=str(res.memory_id),
                        content_snippet=res.content[:500],
                        full_content=res.content,
                        metadata=res.metadata or {},
                    )
                )

            span.set_attribute("rae.federation.results_count", len(fed_results))
            return FederationQueryResponse(results=fed_results)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("federation_query_failed", error=str(e))
            span.set_attribute("rae.error", True)
            span.set_attribute("rae.error.message", str(e))
            raise HTTPException(
                status_code=500, detail=f"Federation query failed: {str(e)}"
            )
