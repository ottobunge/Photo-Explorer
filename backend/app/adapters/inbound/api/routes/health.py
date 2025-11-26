"""Health check endpoints for monitoring and orchestration."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.adapters.outbound.ml.ml_services import get_ml_services
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


class MLModelInfo(BaseModel):
    """Information about a single ML model."""

    name: str
    loaded: bool
    type: str  # "clip", "face_detector", "vision", "object_detector", "scene_classifier"


class MLHealthStatus(BaseModel):
    """Health status of ML models."""

    status: str  # "healthy", "degraded", or "unhealthy"
    timestamp: str
    models: list[MLModelInfo]
    details: dict[str, Any] | None = None


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
        timestamp=datetime.now(UTC).isoformat(),
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
        timestamp=datetime.now(UTC).isoformat(),
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
            photos_info = await vector_store.get_collection_info(settings.qdrant_collection_photos)
            faces_info = await vector_store.get_collection_info(settings.qdrant_collection_faces)

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


@router.get("/health/ml", response_model=MLHealthStatus)
async def ml_health_check(response: Response) -> MLHealthStatus:
    """
    Check ML model health and status.

    Verifies that ML models are loaded and operational:
    - CLIP model for semantic search
    - Face detector for face recognition
    - Vision models (object detection, scene classification)

    Returns 200 if all critical models are healthy.
    Returns 503 if critical models are not loaded.

    Returns:
        MLHealthStatus with details about each model
    """
    try:
        # Get ML services instance (creates singleton if not exists)
        ml_services = get_ml_services()

        # Get health check info
        health_info = await ml_services.health_check()

        # Build model info list
        models = [
            MLModelInfo(
                name=health_info.get("clip_model", "unknown"),
                loaded=health_info.get("clip_loaded", False),
                type="clip",
            ),
            MLModelInfo(
                name=health_info.get("face_model", "unknown"),
                loaded=health_info.get("face_loaded", False),
                type="face_detector",
            ),
        ]

        # Check if vision models are initialized (they are lazy-loaded)
        models.append(
            MLModelInfo(
                name="vision_llm",
                loaded=ml_services._vision_loader is not None,
                type="vision",
            )
        )
        models.append(
            MLModelInfo(
                name="object_detector",
                loaded=ml_services._object_detector is not None,
                type="object_detector",
            )
        )
        models.append(
            MLModelInfo(
                name="scene_classifier",
                loaded=ml_services._scene_classifier is not None,
                type="scene_classifier",
            )
        )

        # Determine overall health status
        # Critical models: CLIP and face detector
        critical_models_loaded = health_info.get("clip_loaded", False) and health_info.get(
            "face_loaded", False
        )

        if critical_models_loaded:
            overall_status = "healthy"
        else:
            overall_status = "unhealthy"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        # Get additional details
        details = {
            "clip_embedding_dim": ml_services.get_clip_embedding_dim()
            if health_info.get("clip_loaded", False)
            else None,
            "face_embedding_dim": ml_services.get_face_embedding_dim()
            if health_info.get("face_loaded", False)
            else None,
        }

        return MLHealthStatus(
            status=overall_status,
            timestamp=datetime.now(UTC).isoformat(),
            models=models,
            details=details,
        )

    except Exception as e:
        logger.error(f"ML health check failed: {e}", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return MLHealthStatus(
            status="unhealthy",
            timestamp=datetime.now(UTC).isoformat(),
            models=[],
            details={"error": str(e)},
        )
