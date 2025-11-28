"""Task execution tracking entity for idempotency."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TaskExecutionStatus(str, Enum):
    """Status of a task execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskExecution:
    """
    Task execution tracking entity.

    Used to track Celery task executions and ensure idempotency.
    When a task is retried, we can check if it already completed successfully
    and avoid duplicate processing.
    """

    task_id: str  # Celery task ID
    task_name: str  # Task function name (e.g., "process_photo_task")
    status: TaskExecutionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    error_message: Optional[str] = None
    result: Optional[str] = None  # JSON result if needed

    # Context for the task (e.g., photo_id, connector_id)
    context: Optional[dict[str, object]] = None

    @classmethod
    def create(
        cls,
        task_id: str,
        task_name: str,
        context: Optional[dict[str, object]] = None,
    ) -> "TaskExecution":
        """Create a new task execution record.

        Args:
            task_id: Celery task ID
            task_name: Name of the task function
            context: Optional context dictionary (e.g., {"photo_id": "123"})

        Returns:
            New TaskExecution instance
        """
        return cls(
            task_id=task_id,
            task_name=task_name,
            status=TaskExecutionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            context=context,
        )

    def mark_running(self) -> None:
        """Mark the task as running."""
        self.status = TaskExecutionStatus.RUNNING
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, result: Optional[str] = None) -> None:
        """Mark the task as completed successfully.

        Args:
            result: Optional JSON result string
        """
        self.status = TaskExecutionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result

    def mark_failed(self, error_message: str) -> None:
        """Mark the task as failed.

        Args:
            error_message: Error message describing the failure
        """
        self.status = TaskExecutionStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message

    def mark_retrying(self) -> None:
        """Mark the task as retrying."""
        self.status = TaskExecutionStatus.RETRYING
        self.retries += 1

    def is_completed(self) -> bool:
        """Check if the task completed successfully."""
        return self.status == TaskExecutionStatus.COMPLETED

    def can_retry(self) -> bool:
        """Check if the task can be retried."""
        return self.status in [TaskExecutionStatus.FAILED, TaskExecutionStatus.RETRYING]
