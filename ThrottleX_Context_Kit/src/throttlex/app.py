"""FastAPI application for ThrottleX."""

import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from throttlex import __version__
from throttlex.logging import setup_logging
from throttlex.metrics import metrics
from throttlex.models import EvaluateRequest, EvaluateResponse, Policy
from throttlex.repository import get_repository
from throttlex.service import get_service

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger.info("throttlex_starting", version=__version__)

    repository = get_repository()
    try:
        await repository.connect()
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    yield

    # Shutdown
    await repository.disconnect()
    logger.info("throttlex_stopped")


app = FastAPI(
    title="ThrottleX Rate Limiter API",
    version=__version__,
    description="Multi-tenant API Rate Limiting & Quotas Service",
    lifespan=lifespan,
)


# === Middleware ===


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """Record HTTP metrics for each request."""
    start_time = time.perf_counter()

    response: Response = await call_next(request)

    duration = time.perf_counter() - start_time
    endpoint = request.url.path
    method = request.method

    metrics.http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=response.status_code,
    ).inc()

    metrics.http_request_duration.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)

    return response


# === Health endpoints ===


@app.get("/health", tags=["Health"])
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    repository = get_repository()
    redis_healthy = await repository.health_check()

    status = "healthy" if redis_healthy else "degraded"

    return {
        "status": status,
        "version": __version__,
        "checks": {
            "redis": "ok" if redis_healthy else "error",
        },
    }


@app.get("/ready", tags=["Health"])
async def ready() -> dict[str, str]:
    """Readiness check endpoint."""
    repository = get_repository()
    if not await repository.health_check():
        raise HTTPException(status_code=503, detail="Redis not available")
    return {"status": "ready"}


# === Metrics endpoint ===


@app.get("/metrics", tags=["Observability"])
async def prometheus_metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# === Policy endpoints ===


@app.post("/policies", response_model=Policy, status_code=201, tags=["Policies"])
async def create_policy(policy: Policy) -> Policy:
    """Create or replace a policy for a tenant."""
    service = get_service()
    return await service.create_policy(policy)


@app.get("/policies/{tenant_id}", response_model=list[Policy], tags=["Policies"])
async def get_policies(tenant_id: str) -> list[Policy]:
    """Get all policies for a tenant."""
    service = get_service()
    return await service.get_policies(tenant_id)


@app.delete("/policies/{tenant_id}", status_code=204, tags=["Policies"])
async def delete_policy(tenant_id: str, route: str | None = None) -> Response:
    """Delete a policy."""
    service = get_service()
    deleted = await service.delete_policy(tenant_id, route)
    if not deleted:
        raise HTTPException(status_code=404, detail="Policy not found")
    return Response(status_code=204)


# === Evaluate endpoint ===


@app.post("/evaluate", response_model=EvaluateResponse, tags=["Rate Limiting"])
async def evaluate(request: EvaluateRequest) -> JSONResponse:
    """Evaluate if a request is allowed for a tenant/route."""
    start_time = time.perf_counter()

    service = get_service()
    response, headers = await service.evaluate(request)

    duration = time.perf_counter() - start_time
    metrics.evaluate_duration.labels(tenant_id=request.tenant_id).observe(duration)

    status_code = 200 if response.allow else 429
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(by_alias=True),
        headers={k: str(v) for k, v in headers.items()},
    )


# === Error handlers ===


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def create_app() -> FastAPI:
    """Factory function to create the app."""
    return app
