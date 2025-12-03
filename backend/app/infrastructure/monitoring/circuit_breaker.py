"""Circuit breaker monitoring infrastructure with logging and Prometheus metrics.

This module provides:
- Structured logging for circuit breaker state transitions
- Prometheus metrics for monitoring and alerting
- Correlation ID tracking for distributed tracing
- Detailed state management and recovery tracking
"""

import contextvars
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import ParamSpec, TypeVar
from uuid import UUID, uuid4

from circuitbreaker import CircuitBreakerError  # type: ignore[import-untyped]
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Type variables for decorator
T = TypeVar("T")
P = ParamSpec("P")

# Context variable for correlation IDs (for distributed tracing)
_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


class CircuitBreakerStateEnum(str, Enum):
    """Circuit breaker states for structured logging."""

    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


@dataclass
class CircuitBreakerEvent:
    """Event representing a circuit breaker state change."""

    timestamp: datetime
    operation_name: str
    service_name: str
    method_name: str
    state: CircuitBreakerStateEnum
    previous_state: CircuitBreakerStateEnum | None = None
    error_type: str | None = None
    error_message: str | None = None
    failure_count: int = 0
    failure_threshold: int = 0
    duration_seconds: float = 0.0
    correlation_id: str = ""

    def to_log_dict(self) -> dict[str, str | int | float]:
        """Convert event to dictionary for structured logging."""
        log_dict = {
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation_name,
            "service": self.service_name,
            "method": self.method_name,
            "state": self.state.value,
            "correlation_id": self.correlation_id,
            "duration_seconds": self.duration_seconds,
        }

        if self.previous_state:
            log_dict["previous_state"] = self.previous_state.value

        if self.error_type:
            log_dict["error_type"] = self.error_type

        if self.error_message:
            log_dict["error_message"] = self.error_message

        if self.failure_count > 0:
            log_dict["failure_count"] = self.failure_count

        if self.failure_threshold > 0:
            log_dict["failure_threshold"] = self.failure_threshold

        return log_dict


# Prometheus Metrics

# Gauge: Circuit breaker state (0=closed, 1=half_open, 2=open)
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["service", "method"],
)

# Counter: Total failures (incremented when exceptions occur)
circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures by error type",
    ["service", "method", "error_type"],
)

# Counter: Circuit opens (incremented when threshold exceeded)
circuit_breaker_opens = Counter(
    "circuit_breaker_opens_total",
    "Total times circuit breaker opened due to failure threshold",
    ["service", "method"],
)

# Counter: Circuit recoveries (incremented when circuit transitions from open to half-open)
circuit_breaker_recoveries = Counter(
    "circuit_breaker_recoveries_total",
    "Total times circuit breaker attempted recovery after opening",
    ["service", "method"],
)

# Histogram: Operation duration for Qdrant operations
qdrant_operation_duration = Histogram(
    "qdrant_operation_duration_seconds",
    "Qdrant operation duration in seconds",
    ["operation"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

# Fallback Queue Metrics

# Gauge: Current size of Qdrant fallback queue
fallback_queue_length = Gauge(
    "qdrant_fallback_queue_length",
    "Current number of operations in Qdrant fallback queue",
)

# Counter: Total operations queued to fallback
fallback_queue_enqueued_total = Counter(
    "qdrant_fallback_queue_enqueued_total",
    "Total operations enqueued to Qdrant fallback queue",
    ["operation_type"],
)

# Counter: Total operations successfully processed from fallback queue
fallback_queue_processed_total = Counter(
    "qdrant_fallback_queue_processed_total",
    "Total operations successfully processed from Qdrant fallback queue",
    ["operation_type"],
)

# Counter: Total operations that failed to process from fallback queue
fallback_queue_failed_total = Counter(
    "qdrant_fallback_queue_failed_total",
    "Total operations that failed to process from Qdrant fallback queue",
    ["operation_type"],
)

# Counter: Total operations requeued for retry
fallback_queue_requeued_total = Counter(
    "qdrant_fallback_queue_requeued_total",
    "Total operations requeued for retry from Qdrant fallback queue",
    ["operation_type"],
)

# Histogram: Recovery task execution time
fallback_queue_recovery_duration = Histogram(
    "qdrant_fallback_queue_recovery_duration_seconds",
    "Time to process Qdrant fallback queue batch in seconds",
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid4())


class CircuitBreakerStateTracker:
    """Track circuit breaker state transitions with detailed metrics."""

    def __init__(self, operation_name: str, service_name: str, method_name: str) -> None:
        """Initialize state tracker.

        Args:
            operation_name: Logical name of the operation (e.g., 'store_photo')
            service_name: Name of the service/class (e.g., 'QdrantVectorStore')
            method_name: Name of the method (e.g., 'store_photo_embedding')
        """
        self.operation_name = operation_name
        self.service_name = service_name
        self.method_name = method_name
        self.current_state = CircuitBreakerStateEnum.CLOSED
        self.previous_state: CircuitBreakerStateEnum | None = None
        self.failure_count = 0
        self.failure_threshold = 0
        self.last_failure_time: datetime | None = None
        self.open_time: datetime | None = None
        self.recovery_attempts = 0

    def record_state_change(
        self,
        new_state: CircuitBreakerStateEnum,
        error_type: str | None = None,
        error_message: str | None = None,
        failure_count: int = 0,
        failure_threshold: int = 0,
    ) -> CircuitBreakerEvent:
        """Record a state change and return an event.

        Args:
            new_state: The new circuit breaker state
            error_type: Type of error that triggered the change
            error_message: Error message for context
            failure_count: Current failure count
            failure_threshold: Failure threshold for opening

        Returns:
            CircuitBreakerEvent with transition details
        """
        self.previous_state = self.current_state
        self.current_state = new_state
        self.failure_count = failure_count
        self.failure_threshold = failure_threshold

        if new_state == CircuitBreakerStateEnum.OPEN:
            self.open_time = datetime.now(UTC)
        elif new_state == CircuitBreakerStateEnum.HALF_OPEN:
            self.recovery_attempts += 1
            self.last_failure_time = datetime.now(UTC)
        elif new_state == CircuitBreakerStateEnum.CLOSED:
            self.failure_count = 0
            self.open_time = None
            self.recovery_attempts = 0

        event = CircuitBreakerEvent(
            timestamp=datetime.now(UTC),
            operation_name=self.operation_name,
            service_name=self.service_name,
            method_name=self.method_name,
            state=new_state,
            previous_state=self.previous_state,
            error_type=error_type,
            error_message=error_message,
            failure_count=failure_count,
            failure_threshold=failure_threshold,
            correlation_id=get_correlation_id(),
        )

        return event

    def get_time_open(self) -> float | None:
        """Get the time in seconds the circuit has been open.

        Returns:
            Seconds since circuit opened, or None if not open
        """
        if self.open_time is None:
            return None

        return (datetime.now(UTC) - self.open_time).total_seconds()


def log_circuit_breaker_events(
    func: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    """
    Decorator to log circuit breaker state changes and errors.

    This decorator captures CircuitBreakerError exceptions and logs them with
    contextual information including method name, service, failure threshold,
    and recovery timeout. Other exceptions are re-raised without logging.

    The decorator integrates with correlation IDs for distributed tracing.
    If no correlation ID is present in context, one is generated.

    Args:
        func: The function to decorate

    Returns:
        Decorated function that logs circuit breaker events

    Example:
        @log_circuit_breaker_events
        @circuit(failure_threshold=5, recovery_timeout=60)
        async def store_embedding(self, embedding):
            pass
    """

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Ensure we have a correlation ID
        if not get_correlation_id():
            set_correlation_id(generate_correlation_id())

        try:
            return await func(*args, **kwargs)
        except CircuitBreakerError:
            # Extract service and method from the function
            service_name = func.__qualname__.split(".")[0]
            method_name = func.__name__

            logger.exception(
                "Circuit breaker opened for %s.%s",
                service_name,
                method_name,
                extra={
                    "service": service_name,
                    "method": method_name,
                    "circuit_state": "open",
                    "error_type": "CircuitBreakerError",
                    "correlation_id": get_correlation_id(),
                },
            )
            raise
        except Exception:
            # Re-raise other exceptions without logging
            # (they should be logged at the caller level)
            raise

    return async_wrapper


def monitor_circuit_breaker(
    operation_name: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator to monitor circuit breaker operations with metrics and logging.

    This decorator tracks operation duration, failures, and circuit breaker state
    changes. It increments appropriate Prometheus counters and histograms, and
    logs errors with contextual information.

    Metrics tracked:
    - qdrant_operation_duration_seconds: Operation execution time
    - circuit_breaker_failures_total: Count of failures by error type
    - circuit_breaker_opens_total: Count of circuit breaker openings
    - circuit_breaker_recoveries_total: Count of recovery attempts
    - circuit_breaker_state: Current state (0=closed, 1=half_open, 2=open)

    Logging includes:
    - Circuit state transitions with timestamps
    - Error types and counts
    - Recovery attempts and duration
    - Correlation IDs for distributed tracing

    Args:
        operation_name: Name of operation for metrics (e.g., 'store_photo', 'search_photos')

    Returns:
        Decorator that wraps the function with monitoring logic

    Example:
        @monitor_circuit_breaker("store_photo")
        @circuit(failure_threshold=5, recovery_timeout=60)
        async def store_photo_embedding(self, photo_id, embedding):
            pass

    Raises:
        CircuitBreakerError: If circuit breaker is open
        Other exceptions from the wrapped function
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            service_name = func.__qualname__.split(".")[0]
            method_name = func.__name__

            # Ensure we have a correlation ID
            if not get_correlation_id():
                set_correlation_id(generate_correlation_id())

            # Create state tracker for this operation
            tracker = CircuitBreakerStateTracker(operation_name, service_name, method_name)

            try:
                result = await func(*args, **kwargs)
            except CircuitBreakerError:
                # Circuit breaker is open
                duration = time.time() - start_time
                qdrant_operation_duration.labels(operation=operation_name).observe(duration)

                # Record state change
                event = tracker.record_state_change(
                    CircuitBreakerStateEnum.OPEN,
                    error_type="CircuitBreakerError",
                    error_message="Circuit breaker is open, request blocked",
                )
                event.duration_seconds = duration

                # Increment circuit breaker opens counter
                circuit_breaker_opens.labels(
                    service=service_name,
                    method=method_name,
                ).inc()

                # Increment failures counter
                circuit_breaker_failures.labels(
                    service=service_name,
                    method=method_name,
                    error_type="CircuitBreakerError",
                ).inc()

                # Update circuit breaker state gauge (open = 2)
                circuit_breaker_state.labels(
                    service=service_name,
                    method=method_name,
                ).set(2)

                # Log the event
                logger.exception(
                    "Circuit breaker open: %s.%s (operation=%s, time_open=%.2fs)",
                    service_name,
                    method_name,
                    operation_name,
                    tracker.get_time_open() or 0.0,
                    extra=event.to_log_dict(),
                )

                raise
            except Exception as e:
                # Other exception (service or connection error)
                duration = time.time() - start_time
                qdrant_operation_duration.labels(operation=operation_name).observe(duration)

                # Increment failures counter with specific error type
                error_type = type(e).__name__
                error_message = str(e) if str(e) else error_type

                # Record state change
                event = tracker.record_state_change(
                    CircuitBreakerStateEnum.CLOSED,
                    error_type=error_type,
                    error_message=error_message,
                )
                event.duration_seconds = duration

                circuit_breaker_failures.labels(
                    service=service_name,
                    method=method_name,
                    error_type=error_type,
                ).inc()

                logger.exception(
                    "Error in circuit breaker operation %s.%s (error_type=%s, duration=%.3fs)",
                    service_name,
                    method_name,
                    error_type,
                    duration,
                    extra=event.to_log_dict(),
                )

                raise
            else:
                # Record successful operation
                duration = time.time() - start_time
                qdrant_operation_duration.labels(operation=operation_name).observe(duration)

                # Record state change
                event = tracker.record_state_change(
                    CircuitBreakerStateEnum.CLOSED,
                )
                event.duration_seconds = duration

                # Log successful operation
                logger.debug(
                    "Circuit breaker operation %s.%s completed successfully (duration=%.3fs)",
                    service_name,
                    method_name,
                    duration,
                    extra=event.to_log_dict(),
                )

                # Update circuit breaker state gauge (closed = 0)
                circuit_breaker_state.labels(
                    service=service_name,
                    method=method_name,
                ).set(0)

            return result

        return async_wrapper

    return decorator
