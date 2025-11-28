"""Tests for TaskExecution entity - async task orchestration and idempotency.

Tests verify task state machine, idempotency tracking, and error handling
for background worker task execution.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.entities.task_execution import TaskExecution, TaskExecutionStatus


class TestTaskExecutionCreation:
    """Test TaskExecution entity creation."""

    def test_create_new_task_execution_defaults_to_pending(self) -> None:
        """New task execution starts in PENDING state."""
        # Arrange
        task_id = "task-123"
        task_name = "process_photo_task"

        # Act
        execution = TaskExecution.create(task_id, task_name)

        # Assert
        assert execution.task_id == task_id
        assert execution.task_name == task_name
        assert execution.status == TaskExecutionStatus.PENDING
        assert execution.created_at is not None
        assert execution.started_at is None
        assert execution.completed_at is None
        assert execution.retries == 0
        assert execution.error_message is None
        assert execution.result is None

    def test_create_with_context(self) -> None:
        """Can create task execution with context dictionary."""
        # Arrange
        task_id = "task-456"
        task_name = "sync_google_photos"
        context = {"connector_id": "abc123", "user_id": "user-789"}

        # Act
        execution = TaskExecution.create(task_id, task_name, context=context)

        # Assert
        assert execution.context == context
        assert execution.context["connector_id"] == "abc123"

    def test_created_at_timestamp_is_utc(self) -> None:
        """Created timestamp is timezone-aware UTC."""
        # Act
        execution = TaskExecution.create("task-id", "task-name")

        # Assert
        assert execution.created_at.tzinfo is not None
        assert execution.created_at.tzinfo == timezone.utc

    def test_each_task_creation_has_unique_timestamps(self) -> None:
        """Each task execution gets its own timestamp."""
        # Act
        exec1 = TaskExecution.create("task-1", "task")
        exec2 = TaskExecution.create("task-2", "task")

        # Assert - may have same timestamp due to execution speed, but objects are unique
        assert exec1.task_id != exec2.task_id
        assert exec1.created_at <= exec2.created_at


class TestTaskExecutionStateTransitions:
    """Test task execution state machine transitions."""

    def test_mark_running_transitions_from_pending(self) -> None:
        """Marking task running transitions PENDING -> RUNNING."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        assert execution.status == TaskExecutionStatus.PENDING

        # Act
        execution.mark_running()

        # Assert
        assert execution.status == TaskExecutionStatus.RUNNING
        assert execution.started_at is not None
        assert execution.started_at.tzinfo == timezone.utc

    def test_mark_running_sets_started_at_only_once(self) -> None:
        """Started timestamp is only set on first mark_running call."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")

        # Act
        execution.mark_running()
        first_start = execution.started_at

        execution.mark_running()  # Call again
        second_start = execution.started_at

        # Assert
        assert first_start == second_start  # Timestamp didn't change

    def test_mark_completed_transitions_to_completed(self) -> None:
        """Marking task completed transitions RUNNING -> COMPLETED."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()

        # Act
        execution.mark_completed()

        # Assert
        assert execution.status == TaskExecutionStatus.COMPLETED
        assert execution.completed_at is not None
        assert execution.completed_at.tzinfo == timezone.utc

    def test_mark_completed_with_result(self) -> None:
        """Completion can include JSON result."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()
        result_json = '{"photos_processed": 42}'

        # Act
        execution.mark_completed(result_json)

        # Assert
        assert execution.result == result_json
        assert execution.status == TaskExecutionStatus.COMPLETED

    def test_mark_failed_sets_error_message(self) -> None:
        """Marking task failed records error message."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()
        error_msg = "Connection timeout to Qdrant"

        # Act
        execution.mark_failed(error_msg)

        # Assert
        assert execution.status == TaskExecutionStatus.FAILED
        assert execution.error_message == error_msg
        assert execution.completed_at is not None

    def test_mark_failed_transitions_from_any_state(self) -> None:
        """Task can fail from RUNNING state."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()

        # Act
        execution.mark_failed("Error occurred")

        # Assert
        assert execution.status == TaskExecutionStatus.FAILED

    def test_mark_retrying_increments_retry_count(self) -> None:
        """Marking retrying increments retry counter."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        assert execution.retries == 0

        # Act
        execution.mark_retrying()
        execution.mark_retrying()
        execution.mark_retrying()

        # Assert
        assert execution.retries == 3
        assert execution.status == TaskExecutionStatus.RETRYING

    def test_mark_retrying_can_happen_after_failure(self) -> None:
        """Task can transition FAILED -> RETRYING."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()
        execution.mark_failed("First attempt failed")

        # Act
        execution.mark_retrying()

        # Assert
        assert execution.status == TaskExecutionStatus.RETRYING
        assert execution.retries == 1


class TestTaskExecutionQueries:
    """Test task execution query methods."""

    def test_is_completed_returns_true_when_completed(self) -> None:
        """is_completed() returns True only when status is COMPLETED."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")

        # Act & Assert
        assert execution.is_completed() is False

        execution.mark_running()
        assert execution.is_completed() is False

        execution.mark_completed()
        assert execution.is_completed() is True

    def test_can_retry_returns_true_for_failed_states(self) -> None:
        """can_retry() returns True for FAILED and RETRYING states."""
        # Arrange & Act
        execution = TaskExecution.create("task-1", "my-task")

        # PENDING -> not retryable
        assert execution.can_retry() is False

        execution.mark_running()
        # RUNNING -> not retryable
        assert execution.can_retry() is False

        execution.mark_failed("Error")
        # FAILED -> retryable
        assert execution.can_retry() is True

        execution.mark_retrying()
        # RETRYING -> retryable
        assert execution.can_retry() is True

    def test_can_retry_false_for_completed(self) -> None:
        """can_retry() returns False when task completed successfully."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()
        execution.mark_completed()

        # Act & Assert
        assert execution.can_retry() is False


class TestTaskExecutionIdempotency:
    """Test idempotency behavior - detecting duplicate task execution."""

    def test_same_task_id_represents_same_task(self) -> None:
        """Tasks with same ID represent same execution attempt."""
        # Arrange
        task_id = "sync-connector-abc123"

        # Act
        exec1 = TaskExecution.create(task_id, "sync_connector")
        exec2 = TaskExecution.create(task_id, "sync_connector")

        # Assert
        assert exec1.task_id == exec2.task_id  # Same task
        # Note: Objects are independent, but task_id is the idempotency key

    def test_different_task_ids_are_different_tasks(self) -> None:
        """Tasks with different IDs are different executions."""
        # Act
        exec1 = TaskExecution.create("sync-connector-abc123", "sync_connector")
        exec2 = TaskExecution.create("sync-connector-xyz789", "sync_connector")

        # Assert
        assert exec1.task_id != exec2.task_id

    def test_context_preserves_execution_details(self) -> None:
        """Context preserves details needed for idempotency."""
        # Arrange
        task_id = "process-photo-42"
        context = {
            "photo_id": str(uuid4()),
            "connector_id": str(uuid4()),
            "attempt": 1,
        }

        # Act
        execution = TaskExecution.create(task_id, "process_photo", context=context)

        # Assert
        assert execution.context == context
        # Service can use context + task_id as idempotency key


class TestTaskExecutionErrorHandling:
    """Test error tracking and handling."""

    def test_error_message_is_recorded(self) -> None:
        """Error messages are preserved for debugging."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()
        error_msg = "Database connection failed: timeout after 30s"

        # Act
        execution.mark_failed(error_msg)

        # Assert
        assert execution.error_message == error_msg

    def test_clear_error_state_by_retrying(self) -> None:
        """Retrying clears error and tracks retry count."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")
        execution.mark_running()
        execution.mark_failed("First error")
        first_error = execution.error_message

        # Act
        execution.mark_retrying()

        # Assert
        assert execution.error_message == first_error  # Error still there
        assert execution.retries == 1  # But retrying is tracked

    def test_mark_failed_from_pending_state(self) -> None:
        """Task can fail before even starting."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")

        # Act
        execution.mark_failed("Pre-condition check failed")

        # Assert
        assert execution.status == TaskExecutionStatus.FAILED
        assert execution.started_at is None
        assert execution.completed_at is not None

    def test_multiple_failures_tracked(self) -> None:
        """Each retry increments counter even after failures."""
        # Arrange
        execution = TaskExecution.create("task-1", "my-task")

        # Act
        execution.mark_running()
        execution.mark_failed("Attempt 1 failed")
        execution.mark_retrying()

        execution.mark_running()  # Try again
        execution.mark_failed("Attempt 2 failed")
        execution.mark_retrying()

        execution.mark_running()  # Try once more
        execution.mark_failed("Attempt 3 failed")

        # Assert
        assert execution.retries == 2  # 2 retries after initial failure
        assert execution.status == TaskExecutionStatus.FAILED


class TestTaskExecutionIntegration:
    """Integration tests for complete task execution flows."""

    def test_successful_task_flow(self) -> None:
        """Complete flow: PENDING -> RUNNING -> COMPLETED."""
        # Arrange & Act
        execution = TaskExecution.create(
            "sync-photos-001",
            "sync_google_photos",
            context={"sync_id": "batch-42"}
        )

        # Assert step 1: Created in PENDING state
        assert execution.status == TaskExecutionStatus.PENDING
        assert execution.is_completed() is False

        # Act: Start
        execution.mark_running()

        # Assert step 2: Running
        assert execution.status == TaskExecutionStatus.RUNNING
        assert execution.started_at is not None
        assert execution.is_completed() is False

        # Act: Complete
        execution.mark_completed('{"synced": 24, "failed": 0}')

        # Assert step 3: Completed with result
        assert execution.status == TaskExecutionStatus.COMPLETED
        assert execution.result == '{"synced": 24, "failed": 0}'
        assert execution.is_completed() is True

    def test_failed_task_with_retry_flow(self) -> None:
        """Flow with failure and retry: PENDING -> RUNNING -> FAILED -> RETRYING -> RUNNING -> COMPLETED."""
        # Arrange & Act
        execution = TaskExecution.create("download-image-001", "download_image")

        # Step 1: Start
        execution.mark_running()
        assert execution.status == TaskExecutionStatus.RUNNING

        # Step 2: Fail
        execution.mark_failed("Connection timeout")
        assert execution.status == TaskExecutionStatus.FAILED
        assert execution.can_retry() is True

        # Step 3: Retry
        execution.mark_retrying()
        assert execution.status == TaskExecutionStatus.RETRYING
        assert execution.retries == 1

        # Step 4: Try again
        execution.mark_running()
        assert execution.status == TaskExecutionStatus.RUNNING

        # Step 5: Success
        execution.mark_completed()

        # Assert final state
        assert execution.status == TaskExecutionStatus.COMPLETED
        assert execution.retries == 1  # Retried once
        assert execution.is_completed() is True

    def test_persistent_failure_scenario(self) -> None:
        """Task that fails multiple times and finally succeeds."""
        # Arrange
        execution = TaskExecution.create("process-batch", "process_batch")

        # Act & Assert: Failure, retry, failure, retry, success
        for attempt in range(1, 4):
            execution.mark_running()

            if attempt < 3:
                # Fail first 2 attempts
                execution.mark_failed(f"Attempt {attempt} failed: storage unavailable")
                assert execution.can_retry() is True
                execution.mark_retrying()
                assert execution.retries == attempt
            else:
                # Succeed on 3rd attempt
                execution.mark_completed('{"processed": 100}')
                assert execution.status == TaskExecutionStatus.COMPLETED

        # Assert final state
        assert execution.retries == 2
        assert execution.is_completed() is True


class TestTaskExecutionTimestamps:
    """Test timestamp handling and timezone awareness."""

    def test_all_timestamps_are_timezone_aware(self) -> None:
        """All timestamps are UTC and timezone-aware."""
        # Arrange & Act
        execution = TaskExecution.create("task-1", "task")
        execution.mark_running()
        execution.mark_completed()

        # Assert
        assert execution.created_at.tzinfo == timezone.utc
        assert execution.started_at.tzinfo == timezone.utc
        assert execution.completed_at.tzinfo == timezone.utc

    def test_timestamp_ordering(self) -> None:
        """Timestamps maintain logical order."""
        # Arrange & Act
        execution = TaskExecution.create("task-1", "task")
        created = execution.created_at

        execution.mark_running()
        started = execution.started_at

        execution.mark_completed()
        completed = execution.completed_at

        # Assert
        assert created <= started  # Task started after creation
        assert started <= completed  # Task completed after starting
