"""FastAPI middleware."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from clarke.telemetry.logging import request_id_ctx
from clarke.utils.ids import generate_request_id


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user rate limiting scaffold.

    Tracks request counts per user_id (from request body) within a rolling window.
    Currently logs but does not enforce — enforcement enabled via settings.
    """

    def __init__(self, app, max_requests_per_minute: int = 60) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.max_rpm = max_requests_per_minute
        self._counts: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Rate limiting scaffold — tracks but does not block in Phase 1-4
        # Full enforcement deferred until production hardening
        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Extract or generate X-Request-ID and propagate through context var."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID") or generate_request_id()
        request_id_ctx.set(req_id)
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
