# Worker Error Handling and Retry Logic Guide

## Overview

This document describes the comprehensive error handling and retry logic implemented for all Celery worker tasks in the Photo Explorer application.

## Key Components

### 1. Custom Exception Hierarchy (`exceptions.py`)

All worker exceptions inherit from base classes that indicate whether errors should be retried:

- **`TransientError`**: Temporary failures that should be retried (network issues, rate limits, service unavailability)
- **`PermanentError`**: Failures that won't succeed on retry (invalid data, missing resources, authentication failures)

### Specific Exception Types

#### Transient Errors (Will Retry)
- `NetworkError`: Network connectivity or timeout errors
- `ServiceUnavailableError`: External service temporarily unavailable
- `RateLimitError`: API rate limit exceeded
- `DatabaseConnectionError`: Database connection temporarily unavailable
- `TokenRefreshError`: OAuth token needs refresh

#### Permanent Errors (Won't Retry)
- `ResourceNotFoundError`: Required resource not found
- `InvalidDataError`: Data validation failed
- `AuthenticationError`: Authentication failed
- `ProcessingError`: Processing failed due to invalid input
- `StorageError`: Storage operation failed

### 2. Enhanced Celery Configuration (`celery_app.py`)

#### Custom LoggingTask Class

All tasks automatically log:
- Task start with parameters
- Retry attempts with context
- Success/failure with full details
- Structured logging with extra fields for easy querying

#### Global Configuration

```python
task_default_retry_delay=60  # 60 seconds initial delay
task_max_retries=5  # Maximum retry attempts
task_retry_backoff=True  # Exponential backoff
task_retry_backoff_max=600  # Max 10 minutes between retries
task_retry_jitter=True  # Random jitter to avoid thundering herd
```

### 3. Task Decorator Pattern

All tasks follow this pattern:

```python
@celery_app.task(
    bind=True,
    name="module.task_name",
    autoretry_for=(TransientError, NetworkError, RateLimitError, OperationalError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
)
def task_name(self, param_id: str) -> dict:
    """
    Task description.

    Automatically retries on transient errors with exponential backoff.
    """
    try:
        return run_async(_task_name_async(param_id))
    except PermanentError:
        logger.error(
            f"Permanent error in task, will not retry",
            exc_info=True,
            extra={"param_id": param_id},
        )
        raise
    except TransientError as e:
        logger.warning(
            f"Transient error in task, will retry",
            extra={
                "param_id": param_id,
                "error": str(e),
                "retries": self.request.retries,
            },
        )
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in task", extra={"param_id": param_id})
        raise PermanentError(f"Unexpected error: {str(e)}", {"param_id": param_id})
```

## Task-Specific Error Handling

### Photo Processing Tasks (`photo_processing.py`)

#### Error Categories

1. **Validation Errors** → `InvalidDataError` (Permanent)
   - Invalid UUID format
   - Missing required fields

2. **Storage Errors** → `StorageError` (Permanent)
   - File not found
   - Permission denied
   - Disk space issues

3. **Processing Errors** → `ProcessingError` (Permanent)
   - Corrupted image data
   - Unsupported format
   - ML model failures

4. **Vector Store Errors** → `TransientError` (Retry)
   - Qdrant connection issues
   - Embedding storage failures

#### Key Tasks
- `process_photo_task`: Generate thumbnails, embeddings, and analysis
- `detect_faces_task`: Detect and cluster faces
- `generate_embedding_from_thumbnail_task`: Generate embeddings from Google Photos thumbnails

### Google Photos Sync Tasks (`google_photos_sync.py`)

#### Error Categories

1. **Authentication Errors** → `AuthenticationError` (Permanent)
   - Missing OAuth tokens
   - Invalid credentials
   - Expired refresh tokens (after multiple attempts)

2. **Network Errors** → `NetworkError` (Retry with backoff)
   - Connection timeouts
   - DNS resolution failures
   - SSL/TLS errors

3. **Rate Limit Errors** → `RateLimitError` (Retry with exponential backoff)
   - Google Photos API quota exceeded
   - Uses exponential backoff up to 10 minutes

4. **Token Refresh Errors** → `TokenRefreshError` (Retry once)
   - Token refresh failed temporarily
   - OAuth endpoint unavailable

#### Key Tasks
- `sync_google_photos_task`: Full connector sync
- `refresh_photo_url_task`: Refresh expired baseUrls (60-minute TTL)
- `fetch_google_photo_bytes_task`: Download full-resolution photos
- `import_picker_photos_task`: Import from Picker API

#### Special Considerations for External APIs

- **Exponential Backoff**: Starts at 60s, doubles each retry, max 600s
- **Jitter**: Random delay added to avoid thundering herd
- **Max Retries**: 5 attempts for network issues
- **Immediate Failure**: Authentication errors don't retry

### Connector Sync Tasks (`connector_sync.py`)

#### Error Categories

1. **File System Errors** → Context-dependent
   - File not found during sync → Skip and continue
   - Permission denied → `StorageError` (Permanent)
   - Disk full → `StorageError` (Permanent)

2. **Database Errors** → `DatabaseConnectionError` (Retry)
   - Connection pool exhausted
   - Deadlock detection
   - Network partition

#### Key Tasks
- `sync_local_folder_task`: Full folder scan
- `index_single_file_task`: Single file indexing
- `handle_file_deleted_task`: Handle file deletion
- `handle_file_moved_task`: Handle file move/rename

### Face Clustering Tasks (`face_clustering.py`)

#### Error Categories

1. **Vector Store Errors** → `TransientError` (Retry)
   - Qdrant connection failures
   - Search timeout
   - Index update failures

2. **Database Errors** → `DatabaseConnectionError` (Retry)
   - Cluster assignment updates
   - Transaction rollback

#### Key Tasks
- `cluster_faces_task`: Initial clustering of all faces
- `update_clusters_task`: Incremental clustering for new faces
- `merge_clusters_task`: Merge two clusters

### Photo Analysis Tasks (`photo_analysis.py`)

#### Error Categories

1. **ML Service Errors** → Context-dependent
   - Model loading failure → `TransientError` (Retry)
   - Invalid input → `ProcessingError` (Permanent)
   - GPU OOM → `TransientError` (Retry with backoff)

2. **Storage Errors** → `StorageError` (Permanent)
   - Cannot load photo
   - Corrupted file

#### Key Tasks
- `analyze_photo_task`: Full photo analysis with vision LLM
- `generate_description_task`: Generate photo description
- `answer_question_task`: Visual question answering
- `batch_analyze_task`: Batch processing

## Logging Best Practices

### Structured Logging

All error logs include structured context:

```python
logger.error(
    "Human-readable message",
    exc_info=True,  # Include stack trace
    extra={
        "photo_id": photo_id,
        "connector_id": connector_id,
        "error_type": type(exc).__name__,
        "retries": self.request.retries,
    },
)
```

### Log Levels

- **ERROR**: Permanent failures, will not retry
- **WARNING**: Transient failures, will retry
- **INFO**: Successful task completion
- **DEBUG**: Detailed operation steps

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Task Failure Rate**: Permanent errors indicate bugs or configuration issues
2. **Retry Rate**: High retry rates indicate infrastructure problems
3. **Retry Backoff Time**: Long backoff times indicate persistent issues
4. **Exception Types**: Track which errors are most common

### Alert Thresholds

- **Authentication Errors**: Alert immediately (likely configuration issue)
- **High Retry Rate** (>10%): Alert after 5 minutes
- **Database Connection Errors**: Alert if sustained >1 minute
- **Storage Errors**: Alert immediately (disk space issues)

## Testing Error Handling

### Unit Tests

Test each exception type:
```python
def test_permanent_error_no_retry():
    # Test that permanent errors don't trigger retries
    pass

def test_transient_error_retries():
    # Test that transient errors retry with backoff
    pass
```

### Integration Tests

Test retry behavior with real services:
```python
async def test_network_failure_retry():
    # Simulate network failure, verify retry with backoff
    pass
```

## Migration Notes

### Before (Problematic Pattern)

```python
@celery_app.task
def process_photo(photo_id):
    try:
        # ... work ...
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "message": str(e)}
```

**Problems:**
- All errors treated the same
- No retry logic
- Silent failures
- No context logging
- Returns error dict instead of raising

### After (Correct Pattern)

```python
@celery_app.task(
    bind=True,
    autoretry_for=(TransientError, NetworkError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def process_photo(self, photo_id):
    try:
        return run_async(_process_photo_async(photo_id))
    except PermanentError:
        logger.error("Permanent failure", exc_info=True, extra={"photo_id": photo_id})
        raise
    except TransientError as e:
        logger.warning("Transient failure, will retry", extra={"photo_id": photo_id, "retries": self.request.retries})
        raise
```

**Improvements:**
- Distinguishes transient vs permanent errors
- Automatic retry with exponential backoff
- Comprehensive logging with context
- Raises exceptions for Celery to handle
- Tracks retry attempts

## Summary

This error handling implementation provides:

1. **Resilience**: Automatic retry for transient failures
2. **Observability**: Structured logging with full context
3. **Efficiency**: Exponential backoff prevents resource exhaustion
4. **Clarity**: Clear distinction between retriable and permanent errors
5. **Production-Ready**: Handles real-world failure scenarios

All worker tasks now follow these patterns for consistent, reliable operation in production environments.
