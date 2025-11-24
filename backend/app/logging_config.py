"""Structured logging configuration for the application."""

import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Any

import orjson


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs log records as JSON for easy parsing and ingestion
    into log aggregation systems like ELK, Loki, or CloudWatch.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location information
        log_data["location"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add process/thread information
        log_data["process"] = {
            "id": record.process,
            "name": record.processName,
        }
        log_data["thread"] = {
            "id": record.thread,
            "name": record.threadName,
        }

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from LogRecord (for contextual logging)
        # These are fields added via logger.info("msg", extra={...})
        if hasattr(record, "extra_fields"):
            log_data["context"] = record.extra_fields
        else:
            # Check for common context fields
            context_fields = {}
            for field in [
                "request_id",
                "user_id",
                "photo_id",
                "face_id",
                "album_id",
                "connector_id",
                "task_id",
                "task_name",
                "session_id",
                "ip_address",
                "user_agent",
            ]:
                if hasattr(record, field):
                    context_fields[field] = getattr(record, field)

            if context_fields:
                log_data["context"] = context_fields

        # Serialize to JSON using orjson (faster than standard json)
        return orjson.dumps(log_data).decode("utf-8")


class ContextFilter(logging.Filter):
    """
    Logging filter that adds contextual information to log records.

    This can be used to add request-specific context that's available
    via context variables.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record if not already present."""
        # Try to get request context from contextvars
        try:
            from contextvars import ContextVar

            # These would be set by middleware
            request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
            user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)

            request_id = request_id_var.get()
            user_id = user_id_var.get()

            if request_id and not hasattr(record, "request_id"):
                record.request_id = request_id
            if user_id and not hasattr(record, "user_id"):
                record.user_id = user_id
        except (ImportError, LookupError):
            pass

        return True


def setup_logging(
    level: str = "INFO",
    json_logs: bool = True,
    debug: bool = False,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to use JSON formatting (True for production)
        debug: Enable debug mode with more verbose logging
    """
    log_level = logging.DEBUG if debug else getattr(logging, level.upper())

    # Choose formatter based on environment
    formatter_class = JSONFormatter if json_logs else logging.Formatter
    formatter_args = {} if json_logs else {
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    }

    # Configure root logger
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "context_filter": {
                "()": ContextFilter,
            },
        },
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if json_logs else "standard",
                "filters": ["context_filter"],
                "stream": sys.stdout,
            },
            "error_console": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "json" if json_logs else "standard",
                "filters": ["context_filter"],
                "stream": sys.stderr,
            },
        },
        "loggers": {
            # Application loggers
            "app": {
                "level": log_level,
                "handlers": ["console", "error_console"],
                "propagate": False,
            },
            # FastAPI
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            # SQLAlchemy
            "sqlalchemy.engine": {
                "level": "WARNING" if not debug else "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            # Celery
            "celery": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            # External libraries (reduce noise)
            "httpx": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "httpcore": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "error_console"],
        },
    }

    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any,
) -> None:
    """
    Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields to include

    Example:
        log_with_context(
            logger,
            "info",
            "Photo processed successfully",
            photo_id=photo.id,
            processing_time_ms=elapsed,
        )
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=context)
