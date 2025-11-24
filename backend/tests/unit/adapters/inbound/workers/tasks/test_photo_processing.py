"""Unit tests for photo processing worker tasks."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app.adapters.inbound.workers.exceptions import (
    PermanentError,
    ResourceNotFoundError,
    TransientError,
)
from app.adapters.inbound.workers.tasks.photo_processing import (
    process_photo_task,
    run_async,
)


class TestRunAsyncHelper:
    """Tests for run_async helper function."""

    def test_run_async_executes_coroutine(self):
        """When running coroutine, it should return result."""

        async def sample_coro():
            return "test_result"

        result = run_async(sample_coro())

        assert result == "test_result"

    def test_run_async_handles_coroutine_exceptions(self):
        """When coroutine raises exception, it should be propagated."""

        async def failing_coro():
            raise ValueError("Test error")

        with pytest.raises(ValueError) as exc:
            run_async(failing_coro())

        assert "Test error" in str(exc.value)

    def test_run_async_creates_new_event_loop(self):
        """When running async, it should create and close new event loop."""
        import asyncio

        original_loop = None
        try:
            original_loop = asyncio.get_event_loop()
        except RuntimeError:
            pass  # No loop running

        async def sample_coro():
            return asyncio.get_event_loop()

        loop_in_coro = run_async(sample_coro())

        # The loop used in coroutine should be different and closed
        if original_loop:
            assert loop_in_coro is not original_loop
        assert loop_in_coro.is_closed()


class TestProcessPhotoTask:
    """Tests for process_photo_task Celery task."""

    @patch(
        "app.adapters.inbound.workers.tasks.photo_processing._process_photo_async"
    )
    def test_process_photo_task_success(self, mock_process_async):
        """When processing succeeds, it should return results."""
        mock_process_async.return_value = {
            "status": "completed",
            "embedding_created": True,
            "faces_detected": 2,
        }

        photo_id = str(uuid4())
        result = process_photo_task(photo_id)

        assert result["status"] == "completed"
        assert result["embedding_created"] is True
        assert result["faces_detected"] == 2

    @patch(
        "app.adapters.inbound.workers.tasks.photo_processing._process_photo_async"
    )
    def test_process_photo_task_handles_permanent_error(self, mock_process_async):
        """When permanent error occurs, it should not retry."""
        mock_process_async.side_effect = PermanentError("Invalid photo format")

        photo_id = str(uuid4())

        # Create a mock task with request context
        mock_task = Mock()
        mock_task.request = Mock(retries=0)

        with pytest.raises(PermanentError):
            process_photo_task.apply(args=[photo_id]).get()

    @patch(
        "app.adapters.inbound.workers.tasks.photo_processing._process_photo_async"
    )
    def test_process_photo_task_handles_transient_error(self, mock_process_async):
        """When transient error occurs, it should retry."""
        mock_process_async.side_effect = TransientError("Database temporarily unavailable")

        photo_id = str(uuid4())

        # Create a mock task with request context
        mock_task = Mock()
        mock_task.request = Mock(retries=0)

        with pytest.raises(TransientError):
            process_photo_task.apply(args=[photo_id]).get()

    @patch(
        "app.adapters.inbound.workers.tasks.photo_processing._process_photo_async"
    )
    def test_process_photo_task_converts_unknown_error_to_permanent(
        self, mock_process_async
    ):
        """When unknown error occurs, it should convert to PermanentError."""
        mock_process_async.side_effect = ValueError("Unexpected error")

        photo_id = str(uuid4())

        with pytest.raises(PermanentError) as exc:
            process_photo_task.apply(args=[photo_id]).get()

        assert "Unexpected error" in str(exc.value)

    @patch(
        "app.adapters.inbound.workers.tasks.photo_processing._process_photo_async"
    )
    def test_process_photo_task_retries_on_operational_error(self, mock_process_async):
        """When OperationalError occurs, task should be configured to retry."""
        # This test verifies the task decorator configuration
        # The actual retry is handled by Celery, we just check the config
        assert OperationalError in process_photo_task.autoretry_for
        assert process_photo_task.retry_kwargs["max_retries"] == 5
        assert process_photo_task.retry_backoff is True


class TestProcessPhotoAsyncLogic:
    """Tests for photo processing logic (would need full async test setup)."""

    @pytest.mark.asyncio
    @patch("app.adapters.inbound.workers.tasks.photo_processing.get_worker_session_context")
    @patch("app.adapters.inbound.workers.tasks.photo_processing.PhotoRepositoryPostgres")
    @patch("app.adapters.inbound.workers.tasks.photo_processing.get_ml_services")
    @patch("app.adapters.inbound.workers.tasks.photo_processing.LocalFileStorage")
    @patch("app.adapters.inbound.workers.tasks.photo_processing.QdrantVectorStore")
    async def test_process_photo_async_handles_photo_not_found(
        self,
        mock_vector_store,
        mock_file_storage,
        mock_ml_services,
        mock_photo_repo,
        mock_session_context,
    ):
        """When photo not found, it should raise ResourceNotFoundError."""
        # This is a simplified test - full implementation would need more mocking
        # Mock session context
        mock_session = AsyncMock()
        mock_session_context.return_value.__aenter__.return_value = mock_session

        # Mock photo repository to return None (photo not found)
        mock_repo_instance = AsyncMock()
        mock_repo_instance.find_by_id.return_value = None
        mock_photo_repo.return_value = mock_repo_instance

        from app.adapters.inbound.workers.tasks.photo_processing import (
            _process_photo_async,
        )

        photo_id = str(uuid4())

        with pytest.raises(ResourceNotFoundError):
            await _process_photo_async(photo_id)


class TestWorkerTaskConfiguration:
    """Tests for worker task configuration and retry behavior."""

    def test_process_photo_task_has_correct_retry_config(self):
        """When task is configured, it should have proper retry settings."""
        # Verify task configuration
        assert process_photo_task.name == "photo_processing.process_photo"
        assert process_photo_task.bind is True
        assert TransientError in process_photo_task.autoretry_for
        assert OperationalError in process_photo_task.autoretry_for
        assert OSError in process_photo_task.autoretry_for
        assert process_photo_task.retry_backoff is True
        assert process_photo_task.retry_backoff_max == 600
        assert process_photo_task.retry_kwargs["max_retries"] == 5

    def test_task_retry_for_includes_transient_errors(self):
        """When transient errors occur, they should trigger retry."""
        # Verify TransientError and its subclasses would trigger retry
        from app.adapters.inbound.workers.exceptions import (
            DatabaseConnectionError,
            NetworkError,
        )

        # These should all be subclasses of TransientError
        assert issubclass(DatabaseConnectionError, TransientError)
        assert issubclass(NetworkError, TransientError)


class TestErrorClassification:
    """Tests for proper error classification in worker tasks."""

    def test_permanent_errors_should_not_retry(self):
        """When PermanentError occurs, it should not be in autoretry_for."""
        assert PermanentError not in process_photo_task.autoretry_for

    def test_transient_errors_should_retry(self):
        """When TransientError occurs, it should be in autoretry_for."""
        assert TransientError in process_photo_task.autoretry_for

    def test_operational_error_should_retry(self):
        """When database OperationalError occurs, it should retry."""
        assert OperationalError in process_photo_task.autoretry_for
