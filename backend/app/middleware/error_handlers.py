"""Standardized error response handlers for consistent API error format.

All errors return a consistent schema:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {...}  // Optional additional context
    },
    "request_id": "uuid"  // For tracing
}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import (
    AlbumNotFoundError,
    ClusteringInProgressError,
    ConnectorAlreadyExistsError,
    ConnectorNotFoundError,
    DomainException,
    EntityNotFoundException,
    FaceClusterNotFoundError,
    FaceNotFoundError,
    FileNotFoundError,
    InsufficientStorageError,
    InvalidOperationException,
    ModelInferenceError,
    ModelNotLoadedError,
    PhotoAlreadyExistsError,
    PhotoNotFoundError,
    StorageError,
    SyncInProgressError,
    TokenExpiredError,
    TokenNotFoundError,
    ValidationException,
)

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    success: bool = False
    error: ErrorDetail
    request_id: str | None = None


def get_request_id_from_request(request: Request) -> str | None:
    """Extract request ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string or None if not available
    """
    return getattr(request.state, "request_id", None)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with standardized format.

    Args:
        request: FastAPI request object
        exc: HTTP exception that was raised

    Returns:
        JSON response with standardized error format
    """
    request_id = get_request_id_from_request(request)

    # Map HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    error_response = ErrorResponse(
        success=False,
        error=ErrorDetail(
            code=error_code,
            message=str(exc.detail),
            details={"status_code": exc.status_code},
        ),
        request_id=request_id,
    )

    # Log the error with context
    logger.warning(
        "HTTP exception occurred",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "error_code": error_code,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors with standardized format.

    Args:
        request: FastAPI request object
        exc: Validation error from Pydantic

    Returns:
        JSON response with detailed validation errors
    """
    request_id = get_request_id_from_request(request)

    # Format validation errors for better readability
    validation_errors = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        validation_errors.append(
            {
                "field": loc,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    error_response = ErrorResponse(
        success=False,
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={
                "validation_errors": validation_errors,
                "error_count": len(validation_errors),
            },
        ),
        request_id=request_id,
    )

    logger.warning(
        "Validation error occurred",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "validation_errors": validation_errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors with standardized format.

    Args:
        request: FastAPI request object
        exc: Rate limit exceeded exception

    Returns:
        JSON response with rate limit details and Retry-After header
    """
    request_id = get_request_id_from_request(request)

    error_response = ErrorResponse(
        success=False,
        error=ErrorDetail(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests. Please try again later.",
            details={
                "limit": str(exc.detail),
            },
        ),
        request_id=request_id,
    )

    logger.warning(
        "Rate limit exceeded",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "limit_detail": str(exc.detail),
        },
    )

    # Calculate retry after seconds (slowapi should provide this)
    retry_after = getattr(exc, "retry_after", 60)

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response.model_dump(),
        headers={"Retry-After": str(retry_after)},
    )


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Handle domain-specific exceptions with standardized format.

    Maps domain exceptions to appropriate HTTP status codes and error messages.

    Args:
        request: FastAPI request object
        exc: Domain exception that was raised

    Returns:
        JSON response with domain error details
    """
    request_id = get_request_id_from_request(request)

    # Map domain exceptions to HTTP status codes and error codes
    status_code_map: dict[type[DomainException], tuple[int, str]] = {
        # Not Found errors (404)
        EntityNotFoundException: (status.HTTP_404_NOT_FOUND, "ENTITY_NOT_FOUND"),
        ConnectorNotFoundError: (status.HTTP_404_NOT_FOUND, "CONNECTOR_NOT_FOUND"),
        PhotoNotFoundError: (status.HTTP_404_NOT_FOUND, "PHOTO_NOT_FOUND"),
        AlbumNotFoundError: (status.HTTP_404_NOT_FOUND, "ALBUM_NOT_FOUND"),
        FaceNotFoundError: (status.HTTP_404_NOT_FOUND, "FACE_NOT_FOUND"),
        FaceClusterNotFoundError: (status.HTTP_404_NOT_FOUND, "FACE_CLUSTER_NOT_FOUND"),
        FileNotFoundError: (status.HTTP_404_NOT_FOUND, "FILE_NOT_FOUND"),
        TokenNotFoundError: (status.HTTP_404_NOT_FOUND, "TOKEN_NOT_FOUND"),
        # Validation errors (400)
        ValidationException: (status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR"),
        # Conflict errors (409)
        ConnectorAlreadyExistsError: (status.HTTP_409_CONFLICT, "CONNECTOR_ALREADY_EXISTS"),
        PhotoAlreadyExistsError: (status.HTTP_409_CONFLICT, "PHOTO_ALREADY_EXISTS"),
        SyncInProgressError: (status.HTTP_409_CONFLICT, "SYNC_IN_PROGRESS"),
        ClusteringInProgressError: (status.HTTP_409_CONFLICT, "CLUSTERING_IN_PROGRESS"),
        InvalidOperationException: (status.HTTP_409_CONFLICT, "INVALID_OPERATION"),
        # Authentication errors (401)
        TokenExpiredError: (status.HTTP_401_UNAUTHORIZED, "TOKEN_EXPIRED"),
        # Storage errors (507 or 500)
        InsufficientStorageError: (
            status.HTTP_507_INSUFFICIENT_STORAGE,
            "INSUFFICIENT_STORAGE",
        ),
        StorageError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "STORAGE_ERROR"),
        # ML Model errors (503)
        ModelNotLoadedError: (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "MODEL_NOT_LOADED",
        ),
        ModelInferenceError: (
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "MODEL_INFERENCE_ERROR",
        ),
    }

    # Find the most specific exception type
    exc_type = type(exc)
    status_code, error_code = status_code_map.get(
        exc_type,
        (status.HTTP_400_BAD_REQUEST, "DOMAIN_ERROR"),
    )

    # Build error details based on exception type
    details = {}
    if isinstance(exc, EntityNotFoundException):
        details = {
            "entity_type": exc.entity_type,
            "entity_id": exc.entity_id,
        }
    elif isinstance(exc, (TokenExpiredError, TokenNotFoundError, SyncInProgressError)):
        details = {"connector_id": exc.connector_id}
    elif isinstance(exc, InsufficientStorageError):
        details = {
            "required_bytes": exc.required_bytes,
            "available_bytes": exc.available_bytes,
        }
    elif isinstance(exc, ModelNotLoadedError):
        details = {"model_name": exc.model_name}
    elif isinstance(exc, ModelInferenceError):
        details = {
            "model_name": exc.model_name,
            "reason": exc.reason,
        }

    error_response = ErrorResponse(
        success=False,
        error=ErrorDetail(
            code=error_code,
            message=exc.message,
            details=details if details else None,
        ),
        request_id=request_id,
    )

    # Log based on severity
    log_level = logging.INFO if status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        f"Domain exception: {error_code}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "status_code": status_code,
            "error_code": error_code,
        },
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions with standardized format.

    Args:
        request: FastAPI request object
        exc: Unhandled exception

    Returns:
        JSON response with generic error message (hiding internal details)
    """
    request_id = get_request_id_from_request(request)

    error_response = ErrorResponse(
        success=False,
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
            details=None,  # Don't expose internal error details in production
        ),
        request_id=request_id,
    )

    # Log the full exception with traceback
    logger.exception(
        "Unhandled exception occurred",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


def setup_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Domain exceptions (custom business logic errors)
    app.add_exception_handler(DomainException, domain_exception_handler)

    # HTTP exceptions (404, 500, etc.)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Validation errors (422)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Rate limit errors (429)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Error handlers registered successfully")
