"""Unit tests for worker task idempotency helpers."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.workers.idempotency import (
    check_task_completed,
    get_task_context,
    mark_task_completed,
    mark_task_failed,
    mark_task_retrying,
    mark_task_running,
)
from app.domain.entities.task_execution import TaskExecutionStatus

pytestmark = pytest.mark.asyncio


class TestCheckTaskCompleted:
    """Tests for check_task_completed function."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_check_task_completed_returns_true_when_completed(
        self,
        mock_session: Mock,
    ) -> None:
        """When task already completed, should return True."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"
        completed_task = Mock(spec=TaskExecutionModel)
        completed_task.task_id = task_id
        completed_task.status = TaskExecutionStatus.COMPLETED.value
        completed_task.completed_at = datetime.now(timezone.utc)
        completed_task.task_name = "test_task"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=completed_task)
        mock_session.execute.return_value = mock_result

        # Act
        result = await check_task_completed(mock_session, task_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_task_completed_returns_false_when_not_completed(
        self,
        mock_session: Mock,
    ) -> None:
        """When task not completed, should return False."""
        # Arrange
        task_id = "test-task-123"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Act
        result = await check_task_completed(mock_session, task_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_task_completed_returns_false_when_running(
        self,
        mock_session: Mock,
    ) -> None:
        """When task is running but not completed, should return False."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"
        # The query filters for COMPLETED status, so a RUNNING task won't be found
        # Therefore scalar_one_or_none() should return None
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await check_task_completed(mock_session, task_id)

        # Assert
        assert result is False


class TestMarkTaskRunning:
    """Tests for mark_task_running function."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_mark_task_running_creates_new_record(
        self,
        mock_session: Mock,
    ) -> None:
        """When task doesn't exist, should create new execution record."""
        # Arrange
        task_id = "test-task-123"
        task_name = "test_task"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Act
        execution = await mark_task_running(mock_session, task_id, task_name)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        assert execution is not None

    @pytest.mark.asyncio
    async def test_mark_task_running_updates_existing_record(
        self,
        mock_session: Mock,
    ) -> None:
        """When task exists, should update status to running."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"
        task_name = "test_task"

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id
        existing_task.status = TaskExecutionStatus.FAILED.value

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result

        # Act
        execution = await mark_task_running(mock_session, task_id, task_name)

        # Assert
        assert execution.status == TaskExecutionStatus.RUNNING.value
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_task_running_with_context(
        self,
        mock_session: Mock,
    ) -> None:
        """When context provided, should store it in execution record."""
        # Arrange
        task_id = "test-task-123"
        task_name = "test_task"
        context = {"connector_id": str(uuid4()), "sync_type": "full"}

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Act
        execution = await mark_task_running(mock_session, task_id, task_name, context)

        # Assert
        assert execution is not None
        mock_session.flush.assert_called_once()


class TestMarkTaskCompleted:
    """Tests for mark_task_completed function."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_mark_task_completed_updates_status(
        self,
        mock_session: Mock,
    ) -> None:
        """When marking completed, should update status and timestamp."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id
        existing_task.status = TaskExecutionStatus.RUNNING.value

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result

        # Act
        await mark_task_completed(mock_session, task_id)

        # Assert
        assert existing_task.status == TaskExecutionStatus.COMPLETED.value
        assert existing_task.completed_at is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_task_completed_stores_result(
        self,
        mock_session: Mock,
    ) -> None:
        """When result provided, should serialize and store it."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"
        result: dict[str, Any] = {"status": "success", "photos_synced": 42}

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id

        mock_result_obj = Mock()
        mock_result_obj.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result_obj

        # Act
        await mark_task_completed(mock_session, task_id, result)

        # Assert
        assert existing_task.result is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_task_completed_handles_missing_task(
        self,
        mock_session: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When task doesn't exist, should log warning."""
        # Arrange
        task_id = "nonexistent-task"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Act
        import logging
        with caplog.at_level(logging.WARNING):
            await mark_task_completed(mock_session, task_id)

        # Assert
        assert "not found when marking completed" in caplog.text

    @pytest.mark.asyncio
    async def test_mark_task_completed_handles_serialization_error(
        self,
        mock_session: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When result can't be serialized, should store string representation."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"

        # Create non-serializable object
        class NonSerializable:
            pass

        result = {"obj": NonSerializable()}

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id

        mock_result_obj = Mock()
        mock_result_obj.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result_obj

        # Act
        import logging
        with caplog.at_level(logging.WARNING):
            await mark_task_completed(mock_session, task_id, result)

        # Assert
        assert "Failed to serialize task result" in caplog.text
        assert existing_task.result is not None  # Should still have string representation


class TestMarkTaskFailed:
    """Tests for mark_task_failed function."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_mark_task_failed_updates_status(
        self,
        mock_session: Mock,
    ) -> None:
        """When marking failed, should update status and error message."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"
        error_message = "Something went wrong"

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result

        # Act
        await mark_task_failed(mock_session, task_id, error_message)

        # Assert
        assert existing_task.status == TaskExecutionStatus.FAILED.value
        assert existing_task.error_message == error_message
        assert existing_task.completed_at is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_task_failed_truncates_long_error(
        self,
        mock_session: Mock,
    ) -> None:
        """When error message too long, should truncate to 1000 chars."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"
        error_message = "x" * 2000  # Very long error

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result

        # Act
        await mark_task_failed(mock_session, task_id, error_message)

        # Assert
        assert len(existing_task.error_message) == 1000


class TestMarkTaskRetrying:
    """Tests for mark_task_retrying function."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_mark_task_retrying_increments_retry_count(
        self,
        mock_session: Mock,
    ) -> None:
        """When marking retrying, should increment retry count."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id
        existing_task.retries = 0

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result

        # Act
        await mark_task_retrying(mock_session, task_id)

        # Assert
        assert existing_task.status == TaskExecutionStatus.RETRYING.value
        assert existing_task.retries == 1
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_task_retrying_multiple_times(
        self,
        mock_session: Mock,
    ) -> None:
        """When retrying multiple times, should track count correctly."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "test-task-123"

        existing_task = Mock(spec=TaskExecutionModel)
        existing_task.task_id = task_id
        existing_task.retries = 3

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_task)
        mock_session.execute.return_value = mock_result

        # Act
        await mark_task_retrying(mock_session, task_id)

        # Assert
        assert existing_task.retries == 4


class TestGetTaskContext:
    """Tests for get_task_context function."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_task_context_returns_context(
        self,
        mock_session: Mock,
    ) -> None:
        """When task has context, should return it."""
        # Arrange
        task_id = "test-task-123"
        expected_context = {"connector_id": str(uuid4()), "sync_type": "incremental"}

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=expected_context)
        mock_session.execute.return_value = mock_result

        # Act
        context = await get_task_context(mock_session, task_id)

        # Assert
        assert context == expected_context

    @pytest.mark.asyncio
    async def test_get_task_context_returns_none_when_missing(
        self,
        mock_session: Mock,
    ) -> None:
        """When task has no context, should return None."""
        # Arrange
        task_id = "test-task-123"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Act
        context = await get_task_context(mock_session, task_id)

        # Assert
        assert context is None


class TestIdempotencyWorkflow:
    """Integration-style tests for complete idempotency workflow."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_complete_success_workflow(
        self,
        mock_session: Mock,
    ) -> None:
        """Test complete workflow: start -> running -> completed."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "workflow-task-123"
        task_name = "test_workflow"

        # Mock for check_task_completed (not completed)
        mock_result_check = Mock()
        mock_result_check.scalar_one_or_none = Mock(return_value=None)

        # Mock for mark_task_running (create new)
        mock_result_running = Mock()
        mock_result_running.scalar_one_or_none = Mock(return_value=None)

        # Mock for mark_task_completed (update existing)
        running_task = Mock(spec=TaskExecutionModel)
        running_task.task_id = task_id
        mock_result_completed = Mock()
        mock_result_completed.scalar_one_or_none = Mock(return_value=running_task)

        # Setup execute to return different results based on call order
        mock_session.execute.side_effect = [
            mock_result_check,
            mock_result_running,
            mock_result_completed,
        ]

        # Act
        # Step 1: Check if completed
        is_completed = await check_task_completed(mock_session, task_id)
        assert not is_completed

        # Step 2: Mark as running
        execution = await mark_task_running(mock_session, task_id, task_name)
        assert execution is not None

        # Step 3: Mark as completed
        await mark_task_completed(mock_session, task_id, {"status": "success"})
        assert running_task.status == TaskExecutionStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_retry_workflow(
        self,
        mock_session: Mock,
    ) -> None:
        """Test retry workflow: running -> retrying -> running -> completed."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import TaskExecutionModel

        task_id = "retry-task-123"

        running_task = Mock(spec=TaskExecutionModel)
        running_task.task_id = task_id
        running_task.retries = 0

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=running_task)
        mock_session.execute.return_value = mock_result

        # Act
        # Attempt 1 fails, mark retrying
        await mark_task_retrying(mock_session, task_id)
        assert running_task.status == TaskExecutionStatus.RETRYING.value
        assert running_task.retries == 1

        # Attempt 2 succeeds
        await mark_task_completed(mock_session, task_id, {"status": "success"})
        assert running_task.status == TaskExecutionStatus.COMPLETED.value
