"""Worker-specific exceptions for error handling and retry logic."""

from typing import Optional


class WorkerException(Exception):
    """Base exception for worker errors."""

    def __init__(self, message: str, context: Optional[dict[str, object]] = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(message)


class TransientError(WorkerException):
    """
    Transient errors that should be retried.

    These are temporary failures that are likely to succeed on retry,
    such as network issues, temporary service unavailability, or rate limits.
    """



class PermanentError(WorkerException):
    """
    Permanent errors that should not be retried.

    These are failures that will not succeed even with retries,
    such as invalid data, missing resources, or business logic violations.
    """



# Specific transient errors
class NetworkError(TransientError):
    """Network connectivity or timeout errors."""



class ServiceUnavailableError(TransientError):
    """External service temporarily unavailable."""



class RateLimitError(TransientError):
    """Rate limit exceeded, should retry with backoff."""



class DatabaseConnectionError(TransientError):
    """Database connection temporarily unavailable."""



class TokenRefreshError(TransientError):
    """OAuth token needs refresh."""



# Specific permanent errors
class ResourceNotFoundError(PermanentError):
    """Required resource (photo, connector, etc.) not found."""



class InvalidDataError(PermanentError):
    """Data validation failed."""



class AuthenticationError(PermanentError):
    """Authentication failed (missing or invalid credentials)."""



class ProcessingError(PermanentError):
    """Processing failed due to invalid input or corrupted data."""



class StorageError(PermanentError):
    """Storage operation failed (disk full, permission denied, etc.)."""

