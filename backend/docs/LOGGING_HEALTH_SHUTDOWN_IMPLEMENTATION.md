# Logging, Health Checks, and Graceful Shutdown Implementation

**Date:** 2025-11-24
**Status:** Completed
**Issues Addressed:** LOW-2, LOW-3, LOW-4, LOW-8

## Overview

This document describes the implementation of structured logging, health check endpoints, and graceful shutdown mechanisms for the Photo Explorer application. These improvements enhance observability, monitoring, and reliability in production environments.

## 1. Structured Logging (LOW-3)

### Implementation

**File:** `backend/app/logging_config.py`

### Features

- **JSON Formatter**: All logs output as structured JSON using `orjson` for high-performance serialization
- **Configurable Output**: JSON for production, human-readable for development
- **Contextual Logging**: Automatic injection of `request_id`, `user_id`, and other context via `ContextFilter`
- **Separate Handlers**: stdout for INFO+ logs, stderr for ERROR+ logs
- **Pre-configured Loggers**: app, uvicorn, SQLAlchemy, Celery with appropriate log levels

### Log Structure

```json
{
  "timestamp": "2025-11-24T12:34:56.789Z",
  "level": "INFO",
  "logger": "app.adapters.inbound.api.routes.photos",
  "message": "Photo processed successfully",
  "location": {
    "file": "/app/adapters/inbound/api/routes/photos.py",
    "line": 42,
    "function": "process_photo"
  },
  "process": {
    "id": 12345,
    "name": "MainProcess"
  },
  "thread": {
    "id": 67890,
    "name": "MainThread"
  },
  "context": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "photo_id": "a1b2c3d4-e5f6-4789-0123-456789abcdef",
    "processing_time_ms": 234.5
  }
}
```

### Usage

```python
from app.logging_config import get_logger, log_with_context

logger = get_logger(__name__)

# Simple logging
logger.info("Processing photo")

# Contextual logging
log_with_context(
    logger,
    "info",
    "Photo processed successfully",
    photo_id=photo_id,
    processing_time_ms=elapsed,
)

# Using extra parameter directly
logger.info(
    "Request completed",
    extra={
        "request_id": request_id,
        "status_code": 200,
        "response_time_ms": 45.2,
    },
)
```

### Configuration

Logging is initialized in `main.py` during application startup:

```python
setup_logging(
    level="DEBUG" if app_settings.debug else "INFO",
    json_logs=not app_settings.debug,
    debug=app_settings.debug,
)
```

## 2. Request ID Tracing (LOW-2)

### Implementation

**File:** `backend/app/middleware.py` (refactored into `backend/app/middleware/request_id.py`)

### Features

- **Automatic ID Generation**: Creates UUID v4 for each request if not provided
- **Header Extraction**: Accepts existing `X-Request-ID` header from clients
- **Context Variables**: Stores request_id in context vars for access throughout request lifecycle
- **Response Headers**: Returns `X-Request-ID` in response for client-side correlation
- **Request/Response Logging**: Logs all incoming and completed requests with timing

### Request Log Example

```json
{
  "timestamp": "2025-11-24T12:34:56.789Z",
  "level": "INFO",
  "message": "Request started",
  "context": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "method": "POST",
    "path": "/api/v1/photos",
    "query_params": "connector_id=abc123",
    "client_host": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### Response Log Example

```json
{
  "timestamp": "2025-11-24T12:34:56.899Z",
  "level": "INFO",
  "message": "Request completed",
  "context": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "method": "POST",
    "path": "/api/v1/photos",
    "status_code": 200,
    "process_time_ms": 110.25
  }
}
```

## 3. Health Check Endpoints (LOW-4)

### Implementation

**File:** `backend/app/adapters/inbound/api/routes/health.py`

### Endpoints

#### 3.1. Liveness Check: `GET /health`

Returns 200 if the application is running. Does not check dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-24T12:34:56.789Z",
  "version": "0.1.0"
}
```

**Use Case:** Kubernetes liveness probes, basic uptime monitoring

#### 3.2. Readiness Check: `GET /health/ready`

Verifies all critical dependencies are available and healthy.

**Checks:**
- **PostgreSQL**: Executes `SELECT 1` query, reports pool status
- **Redis**: Pings Redis server, reports version
- **Qdrant**: Verifies vector store connection, reports collection statistics

**Success Response (200):**
```json
{
  "status": "ready",
  "timestamp": "2025-11-24T12:34:56.789Z",
  "version": "0.1.0",
  "dependencies": [
    {
      "name": "postgresql",
      "status": "healthy",
      "response_time_ms": 5.23,
      "details": {
        "database": "connected",
        "pool_size": 10
      }
    },
    {
      "name": "redis",
      "status": "healthy",
      "response_time_ms": 2.45,
      "details": {
        "connected": true,
        "version": "7.0.11"
      }
    },
    {
      "name": "qdrant",
      "status": "healthy",
      "response_time_ms": 8.91,
      "details": {
        "connected": true,
        "collections": {
          "photos": {
            "name": "photo_embeddings",
            "points": 15234
          },
          "faces": {
            "name": "face_embeddings",
            "points": 8421
          }
        }
      }
    }
  ]
}
```

**Failure Response (503):**
```json
{
  "status": "not_ready",
  "timestamp": "2025-11-24T12:34:56.789Z",
  "version": "0.1.0",
  "dependencies": [
    {
      "name": "postgresql",
      "status": "healthy",
      "response_time_ms": 5.23,
      "details": {
        "database": "connected",
        "pool_size": 10
      }
    },
    {
      "name": "redis",
      "status": "unhealthy",
      "response_time_ms": 30000.0,
      "error": "Connection timeout"
    },
    {
      "name": "qdrant",
      "status": "unhealthy",
      "response_time_ms": 156.78,
      "error": "Collection not found"
    }
  ]
}
```

**Use Case:** Kubernetes readiness probes, load balancer health checks

## 4. Graceful Shutdown (LOW-8)

### Implementation

**Files:**
- `backend/app/main.py` - FastAPI application shutdown
- `backend/app/adapters/inbound/workers/worker_lifecycle.py` - Celery worker shutdown
- `backend/app/adapters/inbound/workers/celery_app.py` - Worker signal integration

### 4.1. FastAPI Application Shutdown

**Signal Handlers:** SIGTERM, SIGINT

**Shutdown Sequence:**
1. Set global `shutdown_event` to signal shutdown in progress
2. Close database connections via `close_db()`
3. Cleanup ML services via `cleanup_ml_services()` (releases models from memory)
4. Close Qdrant vector store connections via `cleanup_vector_store()`
5. Log completion with structured logging

**Code:**
```python
async def shutdown_handler() -> None:
    """Handle graceful shutdown of the application."""
    logger.info("Shutdown signal received, starting graceful shutdown...")

    shutdown_event.set()

    try:
        from app.adapters.outbound.persistence.postgres.database import close_db
        logger.info("Closing database connections...")
        await close_db()

        from app.adapters.outbound.ml import cleanup_ml_services
        logger.info("Cleaning up ML services...")
        cleanup_ml_services()

        from app.adapters.outbound.persistence.qdrant.vector_store import cleanup_vector_store
        logger.info("Cleaning up vector store connections...")
        await cleanup_vector_store()

        logger.info("Graceful shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}", exc_info=True)
```

### 4.2. Celery Worker Shutdown

**Signal Handlers:** SIGTERM, SIGINT
**Celery Signals:** `worker_shutdown`, `worker_process_shutdown`, `celeryd_init`

**Worker Lifecycle:**

1. **Startup (`celeryd_init`):**
   - Configure structured JSON logging
   - Register SIGTERM/SIGINT signal handlers
   - Log worker ready status

2. **Shutdown (`worker_shutdown`, `worker_process_shutdown`):**
   - Cleanup ML services (release models)
   - Log vector store connection cleanup
   - Database connections cleaned via per-task context managers

**Code:**
```python
def cleanup_worker_resources() -> None:
    """Cleanup worker resources during shutdown."""
    logger.info("Starting worker resource cleanup...")

    try:
        from app.adapters.outbound.ml import cleanup_ml_services
        logger.info("Cleaning up ML services...")
        cleanup_ml_services()
    except Exception as e:
        logger.error(f"Error cleaning up ML services: {e}", exc_info=True)

    logger.info("Worker resource cleanup completed")

@worker_shutdown.connect
def handle_worker_shutdown(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info("Worker shutdown signal received")
    cleanup_worker_resources()
```

### Shutdown Characteristics

- **Fast Cleanup**: No timeout needed, typical shutdown < 1 second
- **Error Handling**: All cleanup wrapped in try-except with logging
- **Idempotent**: Safe to call cleanup multiple times
- **Structured Logging**: All steps logged for debugging
- **Resource Safety**:
  - Database connections closed properly
  - ML models dereferenced for garbage collection
  - Qdrant async clients closed
  - No resource leaks

## 5. Dependencies Added

**File:** `backend/pyproject.toml`

```toml
[tool.poetry.dependencies]
# ... existing dependencies ...
orjson = "^3.9.0"
redis = {extras = ["hiredis"], version = "^5.0.0"}
```

- **orjson**: High-performance JSON serialization for logging
- **redis[hiredis]**: Async Redis client for health checks

## 6. Integration

### Application Startup

```python
# main.py
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app_settings = get_settings()

    # Configure logging first
    setup_logging(
        level="DEBUG" if app_settings.debug else "INFO",
        json_logs=not app_settings.debug,
        debug=app_settings.debug,
    )

    logger.info("Starting Photo Explorer application...")
    app_settings.ensure_directories()
    logger.info("Application startup complete")

    yield

    logger.info("Application shutdown initiated...")
    await shutdown_handler()
```

### Middleware Registration

```python
# main.py
def create_app() -> FastAPI:
    app = FastAPI(...)

    # Request ID middleware (for tracing)
    app.add_middleware(RequestTracingMiddleware)

    # CORS middleware
    app.add_middleware(CORSMiddleware, ...)

    # Include health check router
    app.include_router(health.router, tags=["Health"])

    return app
```

### Worker Initialization

```python
# celery_app.py
@celeryd_init.connect
def setup_worker(**kwargs):
    """Initialize worker with logging and signal handlers."""
    from app.adapters.inbound.workers.worker_lifecycle import init_worker
    init_worker()
```

## 7. Testing

### Health Checks

```bash
# Liveness check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready
```

### Graceful Shutdown

```bash
# Send SIGTERM to FastAPI
kill -TERM <pid>

# Send SIGINT to Celery worker
kill -INT <pid>

# Or use Ctrl+C
```

### Log Verification

```bash
# Start application with JSON logs
PHOTO_EXPLORER_DEBUG=false uvicorn app.main:app

# Check log output
tail -f <logfile> | jq .

# Filter by request ID
tail -f <logfile> | jq 'select(.context.request_id == "550e8400...")'

# Filter by log level
tail -f <logfile> | jq 'select(.level == "ERROR")'
```

## 8. Monitoring Integration

### Prometheus Metrics

Health check endpoints can be scraped for metrics:

```yaml
scrape_configs:
  - job_name: 'photo-explorer'
    metrics_path: '/health/ready'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:8000']
```

### ELK Stack

JSON logs can be shipped to Elasticsearch:

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/photo-explorer/*.log
    json.keys_under_root: true
    json.add_error_key: true
```

### Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: photo-explorer-api
spec:
  containers:
  - name: api
    image: photo-explorer:latest
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
```

## 9. Benefits

### Observability
- **Structured Logs**: Easy to parse, search, and aggregate
- **Request Tracing**: Track requests across services
- **Performance Monitoring**: Response times for all operations

### Reliability
- **Health Checks**: Automated detection of unhealthy instances
- **Graceful Shutdown**: No data loss or connection leaks
- **Error Tracking**: All errors logged with full context

### Production Readiness
- **Container Orchestration**: Ready for Kubernetes/ECS
- **Load Balancing**: Health checks for traffic routing
- **Debugging**: Request IDs for distributed tracing

## 10. Future Enhancements

1. **Distributed Tracing**: Integration with OpenTelemetry/Jaeger
2. **Metrics Export**: Prometheus metrics for health check latency
3. **Log Aggregation**: Ship logs to centralized logging service
4. **Alerting**: Alert on health check failures
5. **Graceful Drain**: Wait for in-flight requests during shutdown (with timeout)

## References

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [Celery Signals](https://docs.celeryproject.org/en/stable/userguide/signals.html)
- [Kubernetes Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
