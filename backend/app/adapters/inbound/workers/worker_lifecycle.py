"""Worker lifecycle management and graceful shutdown for Celery workers."""

import logging
import signal
import sys
from typing import Any

from celery.signals import worker_process_shutdown, worker_shutdown

logger = logging.getLogger(__name__)


def setup_worker_logging() -> None:
    """Configure structured logging for Celery workers."""
    from app.logging_config import setup_logging

    setup_logging(
        level="INFO",
        json_logs=True,
        debug=False,
    )
    logger.info("Worker logging configured")


def cleanup_worker_resources() -> None:
    """
    Cleanup worker resources during shutdown.

    This is called when a worker is shutting down to ensure
    proper cleanup of database connections, ML models, and vector store.
    """
    logger.info("Starting worker resource cleanup...")

    try:
        # Cleanup ML services
        from app.adapters.outbound.ml import cleanup_ml_services

        logger.info("Cleaning up ML services...")
        cleanup_ml_services()

    except Exception as e:
        logger.error(f"Error cleaning up ML services: {e}", exc_info=True)

    try:
        # Cleanup vector store (needs async context)
        import asyncio

        from app.adapters.outbound.persistence.qdrant.vector_store import (
            cleanup_vector_store,
        )

        logger.info("Cleaning up vector store...")
        # Create a new event loop for cleanup since workers are sync
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(cleanup_vector_store())
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error cleaning up vector store: {e}", exc_info=True)

    try:
        # Database connections are cleaned up per-task via context managers
        logger.info("Database connections cleaned up via context managers")

    except Exception as e:
        logger.error(f"Error during database cleanup: {e}", exc_info=True)

    logger.info("Worker resource cleanup completed")


@worker_shutdown.connect
def handle_worker_shutdown(sender: Any = None, **kwargs: Any) -> None:
    """
    Handle worker shutdown signal.

    This is called when the entire worker process is shutting down.
    """
    logger.info("Worker shutdown signal received")
    cleanup_worker_resources()


@worker_process_shutdown.connect
def handle_worker_process_shutdown(sender: Any = None, **kwargs: Any) -> None:
    """
    Handle worker process shutdown signal.

    This is called when a specific worker process is shutting down
    (e.g., in a multi-process worker pool).
    """
    logger.info("Worker process shutdown signal received")
    cleanup_worker_resources()


def handle_sigterm(signum: int, frame: Any) -> None:
    """
    Handle SIGTERM signal for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received SIGTERM (signal {signum}), initiating graceful shutdown...")
    cleanup_worker_resources()
    sys.exit(0)


def handle_sigint(signum: int, frame: Any) -> None:
    """
    Handle SIGINT signal (Ctrl+C) for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received SIGINT (signal {signum}), initiating graceful shutdown...")
    cleanup_worker_resources()
    sys.exit(0)


def register_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown."""
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigint)
    logger.info("Signal handlers registered for worker")


def init_worker() -> None:
    """
    Initialize worker with logging and signal handlers.

    This should be called when a worker starts up.
    """
    setup_worker_logging()
    register_signal_handlers()
    logger.info("Worker initialization completed")
