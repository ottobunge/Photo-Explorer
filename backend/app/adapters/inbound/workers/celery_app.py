"""Celery application configuration."""

import logging
from typing import Any

from celery import Celery, Task
from celery.signals import (
    celeryd_init,
    worker_ready,
    worker_shutting_down,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celeryd_init.connect
def setup_worker(**kwargs: Any) -> None:
    """Initialize worker with logging and signal handlers."""
    from app.adapters.inbound.workers.worker_lifecycle import init_worker

    init_worker()


@worker_ready.connect
def worker_ready_handler(**kwargs: Any) -> None:
    """Handle worker ready signal."""
    logger.info("Celery worker is ready to accept tasks")


@worker_shutting_down.connect
def worker_shutdown_handler(sig: Any, how: Any, exitcode: Any, **kwargs: Any) -> None:
    """
    Handle graceful worker shutdown.

    This handler is called when the worker receives a shutdown signal.
    It ensures that:
    1. Current tasks are allowed to complete
    2. ML services are properly cleaned up
    3. Database connections are closed
    4. Vector store connections are closed

    Args:
        sig: Signal that triggered shutdown
        how: Shutdown method (warm/cold)
        exitcode: Exit code
        **kwargs: Additional signal arguments
    """
    logger.info(
        f"Worker shutdown initiated (signal={sig}, how={how}, exitcode={exitcode})"
    )

    # Import cleanup functions
    import asyncio

    from app.adapters.outbound.ml import cleanup_ml_services
    from app.adapters.outbound.persistence.postgres.database import (
        cleanup_worker_engine,
    )
    from app.adapters.outbound.persistence.qdrant.vector_store import (
        cleanup_vector_store,
    )

    # Clean up ML services (models, GPU cache, etc.)
    try:
        logger.info("Cleaning up ML services...")
        cleanup_ml_services()
        logger.info("ML services cleanup completed")
    except Exception as e:
        logger.error(f"Error during ML services cleanup: {e}", exc_info=True)

    # Clean up database connections (async)
    try:
        logger.info("Cleaning up database connections...")
        asyncio.run(cleanup_worker_engine())
        logger.info("Database cleanup completed")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}", exc_info=True)

    # Clean up vector store connections (async)
    try:
        logger.info("Cleaning up vector store connections...")
        asyncio.run(cleanup_vector_store())
        logger.info("Vector store cleanup completed")
    except Exception as e:
        logger.error(f"Error during vector store cleanup: {e}", exc_info=True)

    logger.info("Worker shutdown cleanup completed successfully")


class LoggingTask(Task):
    """
    Custom Task class with enhanced logging.

    Provides automatic context logging for task execution,
    retries, and failures.
    """

    def on_failure(
        self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any
    ) -> None:
        """
        Log task failure with context.

        If task has exhausted all retries, send to Dead Letter Queue for investigation.
        """
        logger.error(
            f"Task {self.name} failed",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "task_args": args,  # Renamed to avoid LogRecord conflict
                "task_kwargs": kwargs,  # Renamed for consistency
                "exception": str(exc),
                "exception_type": type(exc).__name__,
            },
            exc_info=True,
        )

        # Check if task has exhausted retries
        max_retries = self.max_retries if self.max_retries is not None else 5
        current_retries = self.request.retries if hasattr(self.request, "retries") else 0

        if current_retries >= max_retries:
            # Send to Dead Letter Queue for investigation
            from app.adapters.inbound.workers.tasks.dlq import handle_dlq_message

            try:
                handle_dlq_message.apply_async(
                    kwargs={
                        "task_name": self.name,
                        "task_id": task_id,
                        "task_args": list(args),
                        "task_kwargs": kwargs,
                        "exception": str(exc),
                        "exception_type": type(exc).__name__,
                        "traceback": str(einfo),
                    },
                    queue="dlq",
                )
                logger.info(
                    f"Task {self.name} sent to Dead Letter Queue after {current_retries} retries",
                    extra={"task_id": task_id, "task_name": self.name},
                )
            except Exception as dlq_error:
                logger.error(
                    f"Failed to send task to DLQ: {dlq_error}",
                    extra={"task_id": task_id, "task_name": self.name},
                )

        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """Log task retry with context."""
        logger.warning(
            f"Task {self.name} retrying",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "task_args": args,  # Renamed to avoid LogRecord conflict
                "task_kwargs": kwargs,  # Renamed for consistency
                "exception": str(exc),
                "exception_type": type(exc).__name__,
                "retries": self.request.retries,
            },
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """Log task success."""
        logger.info(
            f"Task {self.name} completed successfully",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "task_args": args,  # Renamed to avoid LogRecord conflict
                "task_kwargs": kwargs,  # Renamed for consistency
            },
        )
        super().on_success(retval, task_id, args, kwargs)


# Create Celery application with custom task class
celery_app = Celery(
    "photo_explorer",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    task_cls=LoggingTask,
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Task timeout settings (prevent tasks from running indefinitely)
    task_soft_time_limit=3600,  # 1 hour soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=3900,  # 1 hour 5 minutes hard limit (kills task)
    # Retry settings - DO NOT auto-retry all exceptions
    # Individual tasks should define their own retry behavior
    task_default_retry_delay=60,  # 60 seconds initial delay
    task_max_retries=5,  # Default max retries
    task_retry_backoff=True,  # Enable exponential backoff
    task_retry_backoff_max=600,  # Max 10 minutes between retries
    task_retry_jitter=True,  # Add random jitter to avoid thundering herd
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    # Result settings
    result_expires=3600,  # 1 hour
    # Task routing
    task_routes={
        "app.adapters.inbound.workers.tasks.photo_processing.*": {"queue": "processing"},
        "app.adapters.inbound.workers.tasks.face_clustering.*": {"queue": "clustering"},
        "app.adapters.inbound.workers.tasks.connector_sync.*": {"queue": "sync"},
        "app.adapters.inbound.workers.tasks.dlq.*": {"queue": "dlq"},
    },
    # Default queue
    task_default_queue="default",
    # Dead Letter Queue
    task_queues={
        "default": {"x-max-priority": 10},
        "processing": {"x-max-priority": 10},
        "clustering": {"x-max-priority": 5},
        "sync": {"x-max-priority": 10},
        "dlq": {"x-max-priority": 1},  # Low priority for failed tasks
    },
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-orphaned-files": {
            "task": "app.adapters.inbound.workers.tasks.batch_operations.cleanup_orphans_task",
            "schedule": 86400.0,  # Daily
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(
    [
        "app.adapters.inbound.workers.tasks",
    ]
)
