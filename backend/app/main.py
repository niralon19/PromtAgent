from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api import webhooks, feedback, incidents, ws, metrics, knowledge, autonomy
from app.core.config import settings
from app.core.errors import unhandled_exception_handler
from app.core.logging import configure_logging
from app.db.session import engine
import app.tools.examples.grafana_query  # noqa: F401 - registers tools
import app.tools.examples.ssh_check_processes  # noqa: F401
import app.tools.examples.check_data_freshness  # noqa: F401

configure_logging(settings.environment)
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("startup", environment=settings.environment, version=settings.app_version)

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("database_connected")

    from app.tools.registry import tool_registry
    log.info("tools_registered", count=len(tool_registry.list_all()))

    yield

    await engine.dispose()
    log.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestContextMiddleware:
    """Pure ASGI middleware — avoids BaseHTTPMiddleware/call_next asyncpg loop issues."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", str(uuid.uuid4()).encode()).decode()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_request_id(message: Any) -> None:
            if message["type"] == "http.response.start":
                raw_headers: list = list(message.get("headers", []))
                raw_headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": raw_headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)


app.add_middleware(RequestContextMiddleware)


app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

app.include_router(webhooks.router, prefix=settings.api_prefix)
app.include_router(feedback.router)
app.include_router(incidents.router)
app.include_router(ws.router)
app.include_router(metrics.router)
app.include_router(knowledge.router)
app.include_router(autonomy.router)


@app.get("/health", tags=["ops"])
async def health() -> JSONResponse:
    """Returns DB connectivity status. Used by load balancers and readiness probes."""
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        log.error("health_check_db_failed", error=str(exc))

    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "version": settings.app_version,
        },
    )
