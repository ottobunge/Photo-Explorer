"""Request ID middleware for request tracing and correlation.

Generates a unique UUID for each request and propagates it through:
- Response headers (X-Request-ID)
- Log context (for structured logging)
- Database query logging context
- Enables end-to-end request tracing across services
"""

import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and propagate request IDs for tracing.

    Features:
    - Generates UUID v4 for each request (or accepts existing X-Request-ID)
    - Adds X-Request-ID header to all responses
    - Makes request_id available in request.state for use in route handlers
    - Logs request_id for correlation in structured logs
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: ASGI application instance
        """
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and add request ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response with X-Request-ID header
        """
        # Check if request already has an ID (from upstream proxy/gateway)
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            # Generate new UUID for this request
            request_id = str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Set query logger context (for database query logging)
        try:
            from app.middleware.query_logger import set_request_context, clear_request_context

            endpoint = f"{request.method} {request.url.path}"
            set_request_context(endpoint=endpoint, request_id=request_id)
        except ImportError:
            # Query logger not available, skip
            pass

        # Add to logging context (if using structured logging)
        # This allows all logs within this request to include the request_id
        # Note: LoggerAdapter is not a context manager, just use it for logging
        request_logger = logging.LoggerAdapter(logger, {"request_id": request_id})

        try:
            # Process the request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Even on error, include request ID in logs
            logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            raise exc
        finally:
            # Clear query logger context
            try:
                from app.middleware.query_logger import clear_request_context

                clear_request_context()
            except ImportError:
                pass


def get_request_id(request: Request) -> str:
    """Helper function to get request ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string, or empty string if not set
    """
    return getattr(request.state, "request_id", "")
