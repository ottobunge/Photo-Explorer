"""FastAPI middleware for request tracing and logging."""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Context variables for request tracing
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return request_id_var.get()


def get_user_id() -> str | None:
    """Get the current user ID from context."""
    return user_id_var.get()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request ID to all requests and responses.

    This enables request tracing across the application by:
    1. Generating or extracting a request ID for each request
    2. Adding it to the request state and context vars
    3. Including it in the response headers
    4. Logging request/response details with the request ID
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and add tracing information."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in context vars for logging
        request_id_var.set(request_id)

        # Store in request state for easy access
        request.state.request_id = request_id

        # Extract user ID if available (from auth header, etc.)
        # For now, we'll leave this as a placeholder
        user_id = request.headers.get("X-User-ID")
        if user_id:
            user_id_var.set(user_id)
            request.state.user_id = user_id

        # Record start time
        start_time = time.time()

        # Log incoming request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2),
                },
            )

            return response

        except Exception as exc:
            # Calculate processing time
            process_time = time.time() - start_time

            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time_ms": round(process_time * 1000, 2),
                    "exception": str(exc),
                    "exception_type": type(exc).__name__,
                },
                exc_info=True,
            )

            # Re-raise to let FastAPI handle it
            raise

        finally:
            # Clear context vars
            request_id_var.set(None)
            user_id_var.set(None)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log detailed request/response information.

    This is separate from RequestTracingMiddleware to allow
    more granular control over what gets logged.
    """

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Log request and response details."""
        request_id = getattr(request.state, "request_id", None)

        # Log request body if enabled (be careful with sensitive data!)
        if self.log_request_body and request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                logger.debug(
                    "Request body",
                    extra={
                        "request_id": request_id,
                        "content_type": request.headers.get("content-type"),
                        "body_size": len(body),
                        # Don't log actual body to avoid secrets/PII
                        # "body": body.decode("utf-8", errors="ignore"),
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Failed to log request body: {e}",
                    extra={"request_id": request_id},
                )

        # Process request
        response = await call_next(request)

        return response
