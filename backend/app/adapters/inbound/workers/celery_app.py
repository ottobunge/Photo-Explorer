"""Celery application configuration."""

import logging
from typing import Any

from celery import Celery, Task
from celery.signals import (
    celeryd_init,
    worker_ready,
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


class LoggingTask(Task):
    """
    Custom Task class with enhanced logging.

    Provides automatic context logging for task execution,
    retries, and failures.
    """

    def on_failure(
        self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any
    ) -> None:
        """Log task failure with context."""
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
    },
    # Default queue
    task_default_queue="default",
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
