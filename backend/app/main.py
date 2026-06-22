from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router
from app.core.config import settings
from app.core.pg import init_pg_pool, close_pg_pool
from app.core.redis import init_redis, close_redis
from app.core.trace import TraceIdMiddleware
from app.graph.client import close_neo4j


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_pg_pool()
    await init_redis()
    yield
    await close_redis()
    await close_pg_pool()
    await close_neo4j()


app = FastAPI(
    title="Perfume AI Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TraceIdMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Standardized error format per TRD §6.2: {error: {code, message, retryable, details}}."""
    trace_id = getattr(request.state, "trace_id", "")
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "retryable": exc.status_code >= 500,
                    "details": {"trace_id": trace_id},
                }
            },
            headers={"X-Trace-Id": trace_id},
        )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "retryable": True,
                "details": {"trace_id": trace_id},
            }
        },
        headers={"X-Trace-Id": trace_id},
    )


app.include_router(router)
