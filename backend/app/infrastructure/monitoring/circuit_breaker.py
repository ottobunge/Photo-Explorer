"""Circuit breaker monitoring infrastructure with logging and Prometheus metrics."""

import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from circuitbreaker import CircuitBreakerError  # type: ignore[import-untyped]
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Type variables for decorator
T = TypeVar("T")
P = ParamSpec("P")

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

# Histogram: Operation duration for Qdrant operations
qdrant_operation_duration = Histogram(
    "qdrant_operation_duration_seconds",
    "Qdrant operation duration in seconds",
    ["operation"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)


def log_circuit_breaker_events(
    func: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    """
    Decorator to log circuit breaker state changes and errors.

    This decorator captures CircuitBreakerError exceptions and logs them with
    contextual information including method name, service, failure threshold,
    and recovery timeout. Other exceptions are re-raised without logging.

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
    - circuit_breaker_state: Current state (0=closed, 1=half_open, 2=open)

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

            try:
                result = await func(*args, **kwargs)
            except CircuitBreakerError:
                # Circuit breaker is open
                duration = time.time() - start_time
                qdrant_operation_duration.labels(operation=operation_name).observe(duration)

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

                logger.exception(
                    "Circuit breaker open for %s",
                    operation_name,
                    extra={
                        "service": service_name,
                        "method": method_name,
                        "operation": operation_name,
                        "duration_seconds": duration,
                        "circuit_state": "open",
                        "error_type": "CircuitBreakerError",
                    },
                )

                raise
            except Exception as e:
                # Other exception (service or connection error)
                duration = time.time() - start_time
                qdrant_operation_duration.labels(operation=operation_name).observe(duration)

                # Increment failures counter with specific error type
                error_type = type(e).__name__
                circuit_breaker_failures.labels(
                    service=service_name,
                    method=method_name,
                    error_type=error_type,
                ).inc()

                logger.exception(
                    "Error in circuit breaker operation %s: %s",
                    operation_name,
                    error_type,
                    extra={
                        "service": service_name,
                        "method": method_name,
                        "operation": operation_name,
                        "duration_seconds": duration,
                        "error_type": error_type,
                    },
                )

                raise
            else:
                # Record successful operation
                duration = time.time() - start_time
                qdrant_operation_duration.labels(operation=operation_name).observe(duration)

                # Log successful operation
                logger.debug(
                    "Circuit breaker operation %s completed successfully",
                    operation_name,
                    extra={
                        "service": service_name,
                        "method": method_name,
                        "operation": operation_name,
                        "duration_seconds": duration,
                        "circuit_state": "closed",
                    },
                )

                # Update circuit breaker state gauge (closed = 0)
                circuit_breaker_state.labels(
                    service=service_name,
                    method=method_name,
                ).set(0)

            return result

        return async_wrapper

    return decorator
