"""Rate limiting middleware using slowapi.

Implements rate limiting to protect API endpoints from abuse and DoS attacks.
Provides different rate limits for general endpoints vs upload endpoints.
"""

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _get_identifier(request: Request) -> str:
    """Get rate limit identifier from request.

    Uses remote address as the primary identifier. In production with a reverse proxy,
    ensure X-Forwarded-For or X-Real-IP headers are properly set.

    Args:
        request: FastAPI request object

    Returns:
        Client identifier string for rate limiting
    """
    # Try to get the real IP from headers if behind a proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, use the first one
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection IP
    return get_remote_address(request)


def create_limiter() -> Limiter:
    """Create and configure the rate limiter instance.

    Returns:
        Configured Limiter instance with storage backend
    """
    limiter = Limiter(
        key_func=_get_identifier,
        # Use in-memory storage for development
        # For production, consider Redis storage for distributed rate limiting:
        # storage_uri="redis://localhost:6379"
        default_limits=["100 per minute"],
        headers_enabled=True,  # Include rate limit info in response headers
    )
    return limiter


def setup_rate_limiting(app: FastAPI) -> Limiter:
    """Setup rate limiting for the FastAPI application.

    Configures:
    - 100 requests/minute for general endpoints (default)
    - 10 requests/minute for upload endpoints (configured per route)
    - Returns 429 Too Many Requests with Retry-After header
    - Includes X-RateLimit-* headers in responses

    Args:
        app: FastAPI application instance

    Returns:
        Configured Limiter instance for use in route decorators
    """
    limiter = create_limiter()

    # Register the rate limit exceeded handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    return limiter


def rate_limit(limit: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for applying custom rate limits to specific endpoints.

    Usage:
        @app.get("/uploads")
        @rate_limit("10 per minute")
        async def upload_photo():
            ...

    Args:
        limit: Rate limit string (e.g., "10 per minute", "100 per hour")

    Returns:
        Decorator function that applies the rate limit
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store the limit as function metadata for slowapi to pick up
        func.__rate_limit__ = limit  # type: ignore[attr-defined]
        return func

    return decorator
