"""Celery application configuration."""

import logging
import time
from typing import Any

from celery import Celery, Task
from celery.signals import (
    celeryd_init,
    task_postrun,
    task_prerun,
    worker_ready,
    worker_shutting_down,
)
from prometheus_client import Counter, Gauge, Histogram

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Prometheus metrics for Celery tasks
# Task execution time (histogram with buckets for different durations)
task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Task execution duration in seconds",
    ["task_name", "queue"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),  # 1s to 1h
)

# Task failure counter
task_failures_total = Counter(
    "celery_task_failures_total",
    "Total number of task failures",
    ["task_name", "queue", "exception_type"],
)

# Task success counter
task_success_total = Counter(
    "celery_task_success_total",
    "Total number of successful task completions",
    ["task_name", "queue"],
)

# Task retry counter
task_retries_total = Counter(
    "celery_task_retries_total",
    "Total number of task retries",
    ["task_name", "queue"],
)

# Queue depth gauge (approximate based on active tasks)
queue_depth = Gauge(
    "celery_queue_depth",
    "Number of tasks in queue (active)",
    ["queue"],
)

# Active tasks gauge
active_tasks = Gauge(
    "celery_active_tasks",
    "Number of currently executing tasks",
    ["task_name", "queue"],
)


# Task execution tracking (for duration measurement)
_task_start_times = {}


@task_prerun.connect
def task_prerun_handler(task_id: str, task: Task, **kwargs: Any) -> None:
    """Handle task prerun signal - record start time and increment active tasks."""
    _task_start_times[task_id] = time.time()

    # Extract queue name from task request
    queue = getattr(task.request, "delivery_info", {}).get("routing_key", "default")

    # Increment active tasks
    active_tasks.labels(task_name=task.name, queue=queue).inc()


@task_postrun.connect
def task_postrun_handler(
    task_id: str,
    task: Task,
    retval: Any,
    state: str,
    **kwargs: Any,
) -> None:
    """Handle task postrun signal - record duration and update metrics."""
    # Calculate duration
    start_time = _task_start_times.pop(task_id, None)
    if start_time:
        duration = time.time() - start_time

        # Extract queue name
        queue = getattr(task.request, "delivery_info", {}).get("routing_key", "default")

        # Record duration
        task_duration_seconds.labels(task_name=task.name, queue=queue).observe(duration)

        # Decrement active tasks
        active_tasks.labels(task_name=task.name, queue=queue).dec()

        # Record success/failure
        if state == "SUCCESS":
            task_success_total.labels(task_name=task.name, queue=queue).inc()
        elif state == "FAILURE":
            # Try to get exception type from task
            exception_type = "Unknown"
            if hasattr(task, "request") and hasattr(task.request, "exception"):
                exception_type = type(task.request.exception).__name__
            task_failures_total.labels(
                task_name=task.name, queue=queue, exception_type=exception_type
            ).inc()


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
        # Extract queue name
        queue = getattr(self.request, "delivery_info", {}).get("routing_key", "default")

        # Increment retry counter
        task_retries_total.labels(task_name=self.name, queue=queue).inc()

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
