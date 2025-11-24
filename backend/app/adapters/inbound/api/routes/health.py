"""Health check endpoints for monitoring and orchestration."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.adapters.outbound.persistence.postgres.database import get_engine
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health check status response."""

    status: str  # "healthy" or "unhealthy"
    timestamp: str
    version: str = "0.1.0"


class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    name: str
    status: str  # "healthy", "unhealthy", or "degraded"
    response_time_ms: float | None = None
    details: dict[str, Any] | None = None
    error: str | None = None


class ReadinessStatus(BaseModel):
    """Readiness check status with dependency details."""

    status: str  # "ready" or "not_ready"
    timestamp: str
    version: str = "0.1.0"
    dependencies: list[DependencyStatus]


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Basic liveness check.

    This endpoint should return 200 if the application is running.
    It doesn't check dependencies - use /health/ready for that.

    Returns:
        HealthStatus indicating the application is alive
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/ready", response_model=ReadinessStatus)
async def readiness_check(response: Response) -> ReadinessStatus:
    """
    Readiness check with dependency verification.

    Checks all critical dependencies:
    - PostgreSQL database connection
    - Redis connection (via Celery)
    - Qdrant vector store connection

    Returns 200 if all dependencies are healthy.
    Returns 503 if any dependency is unhealthy.

    Returns:
        ReadinessStatus with details about each dependency
    """
    settings = get_settings()
    dependencies: list[DependencyStatus] = []
    all_healthy = True

    # Check PostgreSQL
    pg_status = await check_postgres()
    dependencies.append(pg_status)
    if pg_status.status != "healthy":
        all_healthy = False

    # Check Redis (via ping)
    redis_status = await check_redis()
    dependencies.append(redis_status)
    if redis_status.status != "healthy":
        all_healthy = False

    # Check Qdrant
    qdrant_status = await check_qdrant()
    dependencies.append(qdrant_status)
    if qdrant_status.status != "healthy":
        all_healthy = False

    # Set response status code
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessStatus(
        status="ready" if all_healthy else "not_ready",
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=dependencies,
    )


async def check_postgres() -> DependencyStatus:
    """
    Check PostgreSQL connection health.

    Returns:
        DependencyStatus for PostgreSQL
    """
    import time

    from sqlalchemy import text

    start = time.time()

    try:
        engine = get_engine()

        # Execute a simple query
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            _ = result.scalar()

        response_time = (time.time() - start) * 1000

        return DependencyStatus(
            name="postgresql",
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "database": "connected",
                "pool_size": engine.pool.size() if hasattr(engine.pool, "size") else None,
            },
        )

    except Exception as e:
        response_time = (time.time() - start) * 1000
        logger.error(f"PostgreSQL health check failed: {e}", exc_info=True)
        return DependencyStatus(
            name="postgresql",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            error=str(e),
        )


async def check_redis() -> DependencyStatus:
    """
    Check Redis connection health.

    Returns:
        DependencyStatus for Redis
    """
    import time

    try:
        import redis.asyncio as aioredis

        from app.config import get_settings

        settings = get_settings()
        start = time.time()

        # Create Redis client
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

        try:
            # Ping Redis
            pong = await redis_client.ping()
            response_time = (time.time() - start) * 1000

            if not pong:
                raise Exception("Redis ping returned False")

            # Get some info
            info = await redis_client.info("server")

            await redis_client.aclose()

            return DependencyStatus(
                name="redis",
                status="healthy",
                response_time_ms=round(response_time, 2),
                details={
                    "connected": True,
                    "version": info.get("redis_version"),
                },
            )

        finally:
            await redis_client.aclose()

    except Exception as e:
        response_time = (time.time() - start) * 1000
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        return DependencyStatus(
            name="redis",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            error=str(e),
        )


async def check_qdrant() -> DependencyStatus:
    """
    Check Qdrant vector store health.

    Returns:
        DependencyStatus for Qdrant
    """
    import time

    start = time.time()

    try:
        # Create vector store instance
        vector_store = QdrantVectorStore()

        # Check health
        healthy = await vector_store.health_check()
        response_time = (time.time() - start) * 1000

        if not healthy:
            raise Exception("Qdrant health check returned False")

        # Get collection info
        settings = get_settings()
        try:
            photos_info = await vector_store.get_collection_info(
                settings.qdrant_collection_photos
            )
            faces_info = await vector_store.get_collection_info(
                settings.qdrant_collection_faces
            )

            return DependencyStatus(
                name="qdrant",
                status="healthy",
                response_time_ms=round(response_time, 2),
                details={
                    "connected": True,
                    "collections": {
                        "photos": {
                            "name": photos_info["name"],
                            "points": photos_info["points_count"],
                        },
                        "faces": {
                            "name": faces_info["name"],
                            "points": faces_info["points_count"],
                        },
                    },
                },
            )
        except Exception as info_error:
            # If we can't get collection info but health check passed,
            # still mark as healthy but with limited details
            logger.warning(f"Could not get Qdrant collection info: {info_error}")
            return DependencyStatus(
                name="qdrant",
                status="healthy",
                response_time_ms=round(response_time, 2),
                details={"connected": True, "collections": "unavailable"},
            )

    except Exception as e:
        response_time = (time.time() - start) * 1000
        logger.error(f"Qdrant health check failed: {e}", exc_info=True)
        return DependencyStatus(
            name="qdrant",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            error=str(e),
        )
