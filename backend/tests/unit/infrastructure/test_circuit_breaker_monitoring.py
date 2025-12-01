"""Tests for circuit breaker monitoring infrastructure.

This module tests:
- Correlation ID management
- CircuitBreakerEvent creation and logging
- CircuitBreakerStateTracker state transitions
- Monitor decorator metrics and logging
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from circuitbreaker import CircuitBreakerError

from app.infrastructure.monitoring import (
    CircuitBreakerEvent,
    CircuitBreakerStateEnum,
    CircuitBreakerStateTracker,
    generate_correlation_id,
    get_correlation_id,
    monitor_circuit_breaker,
    set_correlation_id,
)


class TestCorrelationIDManagement:
    """Test correlation ID context variable management."""

    def test_generate_correlation_id_produces_unique_ids(self) -> None:
        """Test that generated correlation IDs are unique."""
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()

        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0

    def test_set_and_get_correlation_id(self) -> None:
        """Test setting and retrieving correlation ID from context."""
        test_id = "test-correlation-id-123"

        set_correlation_id(test_id)
        retrieved_id = get_correlation_id()

        assert retrieved_id == test_id

    def test_default_correlation_id_is_empty(self) -> None:
        """Test that default correlation ID is empty string."""
        # Clear by setting to empty
        set_correlation_id("")

        default_id = get_correlation_id()

        assert default_id == ""

    def test_correlation_id_can_be_updated(self) -> None:
        """Test that correlation ID can be updated."""
        first_id = "first-id"
        second_id = "second-id"

        set_correlation_id(first_id)
        assert get_correlation_id() == first_id

        set_correlation_id(second_id)
        assert get_correlation_id() == second_id


class TestCircuitBreakerEvent:
    """Test CircuitBreakerEvent data structure."""

    def test_event_to_log_dict_includes_all_fields(self) -> None:
        """Test that event converts to log dict with all relevant fields."""
        event = CircuitBreakerEvent(
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
            state=CircuitBreakerStateEnum.OPEN,
            previous_state=CircuitBreakerStateEnum.CLOSED,
            error_type="ConnectionError",
            error_message="Failed to connect to Qdrant",
            failure_count=5,
            failure_threshold=5,
            correlation_id="test-correlation-123",
        )

        log_dict = event.to_log_dict()

        assert log_dict["operation"] == "store_photo"
        assert log_dict["service"] == "QdrantVectorStore"
        assert log_dict["method"] == "store_photo_embedding"
        assert log_dict["state"] == "open"
        assert log_dict["previous_state"] == "closed"
        assert log_dict["error_type"] == "ConnectionError"
        assert log_dict["error_message"] == "Failed to connect to Qdrant"
        assert log_dict["failure_count"] == 5
        assert log_dict["failure_threshold"] == 5
        assert log_dict["correlation_id"] == "test-correlation-123"

    def test_event_excludes_none_fields_from_log_dict(self) -> None:
        """Test that None fields are excluded from log dict."""
        event = CircuitBreakerEvent(
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
            state=CircuitBreakerStateEnum.CLOSED,
            previous_state=None,
            error_type=None,
            error_message=None,
        )

        log_dict = event.to_log_dict()

        assert "previous_state" not in log_dict
        assert "error_type" not in log_dict
        assert "error_message" not in log_dict


class TestCircuitBreakerStateTracker:
    """Test CircuitBreakerStateTracker for state management."""

    def test_initial_state_is_closed(self) -> None:
        """Test that tracker initializes with closed state."""
        tracker = CircuitBreakerStateTracker(
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
        )

        assert tracker.current_state == CircuitBreakerStateEnum.CLOSED
        assert tracker.previous_state is None
        assert tracker.failure_count == 0

    def test_record_state_change_to_open(self) -> None:
        """Test recording state change to open."""
        set_correlation_id("test-123")
        tracker = CircuitBreakerStateTracker(
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
        )

        event = tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.OPEN,
            error_type="ConnectionError",
            failure_count=5,
            failure_threshold=5,
        )

        assert tracker.current_state == CircuitBreakerStateEnum.OPEN
        assert tracker.previous_state == CircuitBreakerStateEnum.CLOSED
        assert event.state == CircuitBreakerStateEnum.OPEN
        assert event.error_type == "ConnectionError"
        assert tracker.open_time is not None

    def test_record_state_change_to_half_open(self) -> None:
        """Test recording state change to half-open (recovery attempt)."""
        tracker = CircuitBreakerStateTracker(
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
        )

        # Transition to open first
        tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.OPEN,
            failure_count=5,
            failure_threshold=5,
        )

        # Then to half-open
        event = tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.HALF_OPEN,
        )

        assert tracker.current_state == CircuitBreakerStateEnum.HALF_OPEN
        assert tracker.previous_state == CircuitBreakerStateEnum.OPEN
        assert tracker.recovery_attempts == 1
        assert event.state == CircuitBreakerStateEnum.HALF_OPEN

    def test_record_state_change_back_to_closed(self) -> None:
        """Test recording successful recovery back to closed."""
        tracker = CircuitBreakerStateTracker(
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
        )

        # Transition through states
        tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.OPEN,
            failure_count=5,
            failure_threshold=5,
        )
        tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.HALF_OPEN,
        )

        # Recovery to closed
        event = tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.CLOSED,
        )

        assert tracker.current_state == CircuitBreakerStateEnum.CLOSED
        assert tracker.previous_state == CircuitBreakerStateEnum.HALF_OPEN
        assert tracker.failure_count == 0
        assert tracker.open_time is None
        assert event.state == CircuitBreakerStateEnum.CLOSED

    def test_get_time_open_returns_none_when_not_open(self) -> None:
        """Test that get_time_open returns None when circuit is not open."""
        tracker = CircuitBreakerStateTracker(
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
        )

        assert tracker.get_time_open() is None

    def test_get_time_open_returns_elapsed_time(self) -> None:
        """Test that get_time_open returns elapsed time when circuit is open."""
        import time

        tracker = CircuitBreakerStateTracker(
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
        )

        tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.OPEN,
            failure_count=5,
            failure_threshold=5,
        )

        # Wait a bit
        time.sleep(0.1)

        elapsed = tracker.get_time_open()

        assert elapsed is not None
        assert elapsed >= 0.1


class TestMonitorCircuitBreakerDecorator:
    """Test monitor_circuit_breaker decorator with monitoring."""

    @pytest.mark.asyncio
    async def test_decorator_logs_successful_operation(self, caplog) -> None:
        """Test that decorator logs successful operations."""
        import logging

        set_correlation_id("test-123")

        # Set log level to capture debug messages
        with caplog.at_level(logging.DEBUG):

            @monitor_circuit_breaker("test_operation")
            async def sample_operation() -> str:
                return "success"

            result = await sample_operation()

            assert result == "success"
            assert "completed successfully" in caplog.text

    @pytest.mark.asyncio
    async def test_decorator_captures_circuit_breaker_error(self) -> None:
        """Test that decorator captures CircuitBreakerError."""
        set_correlation_id("test-123")

        @monitor_circuit_breaker("test_operation")
        async def failing_operation() -> None:
            raise CircuitBreakerError("Circuit is open")

        with pytest.raises(CircuitBreakerError):
            await failing_operation()

    @pytest.mark.asyncio
    async def test_decorator_generates_correlation_id_if_missing(self, caplog) -> None:
        """Test that decorator generates correlation ID if not present."""
        # Clear correlation ID
        set_correlation_id("")

        @monitor_circuit_breaker("test_operation")
        async def sample_operation() -> str:
            return "success"

        await sample_operation()

        # Verify a correlation ID was generated
        current_id = get_correlation_id()
        assert current_id != ""

    @pytest.mark.asyncio
    async def test_decorator_preserves_existing_correlation_id(self) -> None:
        """Test that decorator preserves existing correlation ID."""
        test_id = "preserved-correlation-id-123"
        set_correlation_id(test_id)

        @monitor_circuit_breaker("test_operation")
        async def sample_operation() -> str:
            return "success"

        await sample_operation()

        # Verify correlation ID was preserved
        assert get_correlation_id() == test_id

    @pytest.mark.asyncio
    async def test_decorator_logs_exception_details(self, caplog) -> None:
        """Test that decorator logs exception details."""
        set_correlation_id("test-123")

        @monitor_circuit_breaker("test_operation")
        async def failing_operation() -> None:
            raise ValueError("Test error message")

        with pytest.raises(ValueError):
            await failing_operation()

        assert "Error in circuit breaker operation" in caplog.text
        assert "ValueError" in caplog.text

    @pytest.mark.asyncio
    async def test_decorator_records_operation_duration(self) -> None:
        """Test that decorator records operation duration."""
        import time

        set_correlation_id("test-123")

        @monitor_circuit_breaker("test_operation")
        async def slow_operation() -> str:
            await AsyncMock()()  # Use async mock
            return "done"

        with patch(
            "app.infrastructure.monitoring.circuit_breaker.qdrant_operation_duration"
        ) as mock_duration:
            await slow_operation()

            # Verify duration was observed
            mock_duration.labels.return_value.observe.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_updates_metrics_on_circuit_breaker_error(self) -> None:
        """Test that decorator updates metrics when circuit breaker opens."""
        set_correlation_id("test-123")

        @monitor_circuit_breaker("test_operation")
        async def failing_operation() -> None:
            raise CircuitBreakerError("Circuit is open")

        with patch(
            "app.infrastructure.monitoring.circuit_breaker.circuit_breaker_opens"
        ) as mock_opens:
            with patch(
                "app.infrastructure.monitoring.circuit_breaker.circuit_breaker_failures"
            ) as mock_failures:
                with patch(
                    "app.infrastructure.monitoring.circuit_breaker.circuit_breaker_state"
                ) as mock_state:
                    with pytest.raises(CircuitBreakerError):
                        await failing_operation()

                    # Verify metrics were updated
                    mock_opens.labels.return_value.inc.assert_called_once()
                    mock_failures.labels.return_value.inc.assert_called_once()
                    mock_state.labels.return_value.set.assert_called()

    @pytest.mark.asyncio
    async def test_decorator_updates_metrics_on_other_exception(self) -> None:
        """Test that decorator updates metrics on other exceptions."""
        set_correlation_id("test-123")

        @monitor_circuit_breaker("test_operation")
        async def failing_operation() -> None:
            raise ConnectionError("Connection failed")

        with patch(
            "app.infrastructure.monitoring.circuit_breaker.circuit_breaker_failures"
        ) as mock_failures:
            with pytest.raises(ConnectionError):
                await failing_operation()

            # Verify failure metrics were updated
            mock_failures.labels.return_value.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_sets_closed_state_on_success(self) -> None:
        """Test that decorator sets state to closed on success."""
        set_correlation_id("test-123")

        @monitor_circuit_breaker("test_operation")
        async def successful_operation() -> str:
            return "success"

        with patch(
            "app.infrastructure.monitoring.circuit_breaker.circuit_breaker_state"
        ) as mock_state:
            await successful_operation()

            # Verify state was set to closed (0)
            mock_state.labels.return_value.set.assert_called_with(0)


class TestCircuitBreakerMonitoringIntegration:
    """Integration tests for circuit breaker monitoring."""

    @pytest.mark.asyncio
    async def test_state_transitions_produce_events_with_correlation_ids(self) -> None:
        """Test that state transitions include correlation IDs."""
        correlation_id = "integration-test-123"
        set_correlation_id(correlation_id)

        tracker = CircuitBreakerStateTracker(
            operation_name="store_photo",
            service_name="QdrantVectorStore",
            method_name="store_photo_embedding",
        )

        event1 = tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.OPEN,
            failure_count=5,
            failure_threshold=5,
        )

        assert event1.correlation_id == correlation_id

        event2 = tracker.record_state_change(
            new_state=CircuitBreakerStateEnum.CLOSED,
        )

        assert event2.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_decorator_and_tracker_work_together(self) -> None:
        """Test that decorator and tracker work together seamlessly."""
        correlation_id = "integration-test-456"
        set_correlation_id(correlation_id)

        @monitor_circuit_breaker("integration_test")
        async def test_operation() -> str:
            return "success"

        result = await test_operation()

        assert result == "success"
        assert get_correlation_id() == correlation_id
