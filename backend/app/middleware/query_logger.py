"""Query performance logging middleware for SQLAlchemy.

Logs slow database queries (>100ms) with context for debugging and optimization.
Uses SQLAlchemy event listeners to intercept queries before and after execution.
"""

import logging
import time
from contextvars import ContextVar
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Context variable to store query start time
_query_start_time: ContextVar[dict[str, float]] = ContextVar("_query_start_time", default={})

# Context variable to store request context (endpoint, request_id)
_request_context: ContextVar[dict[str, str]] = ContextVar("_request_context", default={})

# Threshold for slow query logging (milliseconds)
SLOW_QUERY_THRESHOLD_MS = 100


def set_request_context(endpoint: str | None = None, request_id: str | None = None) -> None:
    """Set the current request context for query logging.

    This should be called by a middleware or dependency injection
    to provide context for database queries.

    Args:
        endpoint: The API endpoint being called (e.g., "/api/v1/photos")
        request_id: Unique request identifier for tracing
    """
    context = {}
    if endpoint:
        context["endpoint"] = endpoint
    if request_id:
        context["request_id"] = request_id
    _request_context.set(context)


def clear_request_context() -> None:
    """Clear the request context.

    Should be called after request processing is complete.
    """
    _request_context.set({})


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: tuple | dict,
    context: Any,
    executemany: bool,
) -> None:
    """Record query start time before execution.

    Args:
        conn: Database connection
        cursor: Database cursor
        statement: SQL statement being executed
        parameters: Query parameters
        context: SQLAlchemy execution context
        executemany: Whether this is an executemany() call
    """
    # Store start time keyed by connection id to handle concurrent queries
    conn_id = id(conn)
    start_times = _query_start_time.get({})
    start_times[conn_id] = time.perf_counter()
    _query_start_time.set(start_times)


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: tuple | dict,
    context: Any,
    executemany: bool,
) -> None:
    """Log slow queries after execution.

    Args:
        conn: Database connection
        cursor: Database cursor
        statement: SQL statement that was executed
        parameters: Query parameters
        context: SQLAlchemy execution context
        executemany: Whether this was an executemany() call
    """
    # Calculate execution time
    conn_id = id(conn)
    start_times = _query_start_time.get({})
    start_time = start_times.pop(conn_id, None)
    _query_start_time.set(start_times)

    if start_time is None:
        # No start time recorded (shouldn't happen, but be defensive)
        return

    duration_ms = (time.perf_counter() - start_time) * 1000

    # Only log queries that exceed the threshold
    if duration_ms > SLOW_QUERY_THRESHOLD_MS:
        # Get request context
        req_context = _request_context.get({})

        # Clean up the SQL statement for logging
        # Remove extra whitespace and newlines
        clean_statement = " ".join(statement.split())
        if len(clean_statement) > 500:
            clean_statement = clean_statement[:497] + "..."

        # Format parameters for logging (limit size)
        param_str = str(parameters)
        if len(param_str) > 200:
            param_str = param_str[:197] + "..."

        # Log the slow query with context
        logger.warning(
            f"Slow query detected ({duration_ms:.2f}ms)",
            extra={
                "duration_ms": round(duration_ms, 2),
                "query": clean_statement,
                "parameters": param_str,
                "executemany": executemany,
                "endpoint": req_context.get("endpoint"),
                "request_id": req_context.get("request_id"),
            },
        )


@event.listens_for(Session, "after_transaction_end")
def after_transaction_end(session: Session, transaction: Any) -> None:
    """Clean up query timing data after transaction ends.

    Args:
        session: SQLAlchemy session
        transaction: Transaction object
    """
    # Clean up any lingering timing data for this session
    # This helps prevent memory leaks from abandoned queries
    if hasattr(session, "bind") and session.bind:
        conn_id = id(session.bind)
        start_times = _query_start_time.get({})
        if conn_id in start_times:
            start_times.pop(conn_id, None)
            _query_start_time.set(start_times)


def setup_query_logging() -> None:
    """Initialize query performance logging.

    This function registers SQLAlchemy event listeners for query logging.
    Should be called during application startup.
    """
    logger.info(
        f"Query performance logging enabled (threshold: {SLOW_QUERY_THRESHOLD_MS}ms)"
    )
    # Event listeners are registered via decorators above
    # This function just confirms setup
