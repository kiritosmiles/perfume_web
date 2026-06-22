"""X-Trace-Id middleware — injects trace_id into every response header (TRD §6.2)."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Reuse incoming trace_id header or generate a new one
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        response: Response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response
