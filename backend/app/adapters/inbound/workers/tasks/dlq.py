"""Dead Letter Queue tasks for handling permanently failed tasks."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.adapters.inbound.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.adapters.inbound.workers.tasks.dlq.handle_dlq_message",
    bind=True,
    max_retries=0,  # Don't retry DLQ tasks
)
def handle_dlq_message(
    self,
    task_name: str,
    task_id: str,
    task_args: list[Any],
    task_kwargs: dict[str, Any],
    exception: str,
    exception_type: str,
    traceback: str,
) -> dict[str, Any]:
    """
    Handle permanently failed tasks in the Dead Letter Queue.

    This task logs detailed information about tasks that have exhausted
    all retries and stores them for later investigation.

    Args:
        task_name: Name of the failed task
        task_id: ID of the failed task
        task_args: Positional arguments of the failed task
        task_kwargs: Keyword arguments of the failed task
        exception: String representation of the exception
        exception_type: Type name of the exception
        traceback: Full traceback of the failure

    Returns:
        dict: Summary of the DLQ entry

    Note:
        This task does not retry. Failed tasks are logged to both
        the application logger and a JSON file for investigation.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    dlq_entry = {
        "timestamp": timestamp,
        "task_name": task_name,
        "task_id": task_id,
        "task_args": task_args,
        "task_kwargs": task_kwargs,
        "exception": exception,
        "exception_type": exception_type,
        "traceback": traceback,
    }

    # Log to application logger
    logger.critical(
        f"Dead Letter Queue: Task {task_name} permanently failed",
        extra={
            "dlq_entry": dlq_entry,
            "task_id": task_id,
            "task_name": task_name,
        },
    )

    # Store to DLQ file for investigation
    try:
        dlq_dir = Path("/tmp/photo-explorer-dlq")
        dlq_dir.mkdir(parents=True, exist_ok=True)

        # Create unique filename with timestamp
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dlq_file = dlq_dir / f"dlq_{timestamp_str}_{task_id}.json"

        with dlq_file.open("w") as f:
            json.dump(dlq_entry, f, indent=2)

        logger.info(f"DLQ entry saved to {dlq_file}")

    except Exception as e:
        logger.error(
            f"Failed to save DLQ entry to file: {e}",
            extra={"task_id": task_id, "task_name": task_name},
            exc_info=True,
        )

    return {
        "status": "logged",
        "task_id": task_id,
        "task_name": task_name,
        "timestamp": timestamp,
    }
