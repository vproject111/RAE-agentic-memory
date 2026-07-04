from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SessionContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_id = request.headers.get("X-Session-Id") or request.query_params.get(
            "session_id"
        )
        request.state.session_id = session_id
        response: Response = await call_next(request)
        return response
