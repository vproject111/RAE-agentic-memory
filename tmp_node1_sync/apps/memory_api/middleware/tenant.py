from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-Id") or request.query_params.get(
            "tenant_id"
        )
        request.state.tenant_id = tenant_id
        response: Response = await call_next(request)
        return response
