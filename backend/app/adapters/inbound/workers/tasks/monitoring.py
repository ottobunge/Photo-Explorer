"""Monitoring tasks for system health and resource usage."""

import asyncio
import logging
from typing import Any

from app.adapters.inbound.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):  # type: ignore[no-untyped-def]
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="monitoring.monitor_db_pool",
    time_limit=60,
    soft_time_limit=50,
)
def monitor_db_pool(self: Any) -> dict[str, Any]:
    """
    Monitor database connection pool health.

    Checks the PostgreSQL connection pool status and logs metrics.
    Alerts if the pool is nearly exhausted (>80% checked out).

    Returns:
        Dictionary with pool status
    """
    return run_async(_monitor_db_pool_async())  # type: ignore[no-any-return,no-untyped-call]


async def _monitor_db_pool_async() -> dict[str, Any]:
    """Async implementation of database pool monitoring."""
    from sqlalchemy.pool import QueuePool

    from app.adapters.outbound.persistence.postgres.database import get_worker_session_context

    try:
        # Access engine through session context
        async with get_worker_session_context() as session:
            bind = session.get_bind()

        # Type narrowing: ensure we have an Engine, not a Connection
        if not hasattr(bind, "pool"):
            logger.warning("Database bind does not have a pool attribute")
            return {
                "status": "error",
                "message": "Bind does not have pool attribute",
            }

        pool = bind.pool

        # Check if pool is a QueuePool (the default for PostgreSQL)
        if not isinstance(pool, QueuePool):
            logger.warning(
                f"Database pool is not a QueuePool: {type(pool).__name__}"
            )
            return {
                "status": "error",
                "message": f"Unexpected pool type: {type(pool).__name__}",
            }

        # Get pool status
        pool_status: dict[str, Any] = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "utilization_percent": (
                (pool.checkedout() / pool.size() * 100)
                if pool.size() > 0
                else 0
            ),
        }

        # Log pool status
        logger.info(
            "Database pool status",
            extra={
                "pool_size": pool_status["size"],
                "checked_in": pool_status["checked_in"],
                "checked_out": pool_status["checked_out"],
                "overflow": pool_status["overflow"],
                "utilization_percent": pool_status["utilization_percent"],
            },
        )

        # Alert if pool nearly exhausted
        utilization = pool_status["utilization_percent"]
        if isinstance(utilization, (int, float)) and utilization > 80:
            logger.warning(
                "Database pool nearly exhausted!",
                extra={
                    "utilization_percent": utilization,
                    "checked_out": pool_status["checked_out"],
                    "pool_size": pool_status["size"],
                },
            )
            pool_status["alert"] = "Pool utilization above 80%"

        return {
            "status": "completed",
            "pool_status": pool_status,
        }

    except Exception as e:
        logger.error(
            f"Error monitoring database pool: {e}",
            exc_info=True,
        )
        return {
            "status": "error",
            "message": str(e),
        }
