# Retry Pattern Implementation for Remaining Tasks

This document provides the exact patterns to apply to remaining worker task files.

## Pattern 1: Standard Task with Retry (Apply to most tasks)

```python
@celery_app.task(
    bind=True,
    name="module.task_name",
    autoretry_for=(TransientError, OperationalError, OSError),
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
            f"Permanent error in task_name {param_id}",
            exc_info=True,
            extra={"param_id": param_id},
        )
        raise
    except TransientError as e:
        logger.warning(
            f"Transient error in task_name {param_id}, will retry",
            extra={"param_id": param_id, "error": str(e), "retries": self.request.retries},
        )
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in task_name {param_id}", extra={"param_id": param_id})
        raise PermanentError(f"Unexpected error: {str(e)}", {"param_id": param_id})
```

## Pattern 2: External API Task with Extended Retry (Google Photos, etc.)

```python
@celery_app.task(
    bind=True,
    name="module.api_task_name",
    autoretry_for=(TransientError, NetworkError, RateLimitError, TokenRefreshError, OperationalError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
)
def api_task_name(self, param_id: str) -> dict:
    """
    Task that calls external APIs.

    Retries on network errors, rate limits, and token refresh failures.
    """
    try:
        return run_async(_api_task_async(param_id))
    except (AuthenticationError, InvalidDataError):
        logger.error(
            f"Permanent error in api_task {param_id}",
            exc_info=True,
            extra={"param_id": param_id},
        )
        raise
    except (TransientError, NetworkError, RateLimitError) as e:
        logger.warning(
            f"Transient error in api_task {param_id}, will retry",
            extra={"param_id": param_id, "error": str(e), "error_type": type(e).__name__, "retries": self.request.retries},
        )
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in api_task {param_id}", extra={"param_id": param_id})
        raise PermanentError(f"Unexpected error: {str(e)}", {"param_id": param_id})
```

## Files to Update

### ✅ COMPLETED
- `/backend/app/adapters/inbound/workers/exceptions.py` - Created custom exception hierarchy
- `/backend/app/adapters/inbound/workers/celery_app.py` - Enhanced with LoggingTask class
- `/backend/app/adapters/inbound/workers/tasks/photo_processing.py` - Added retry logic to all tasks

### ⏳ IN PROGRESS
- `/backend/app/adapters/inbound/workers/tasks/google_photos_sync.py` - Added retry to sync_google_photos_task

### 📝 REMAINING (Apply Pattern 1 unless noted)

#### photo_analysis.py
Add imports:
```python
from sqlalchemy.exc import DBAPIError, OperationalError
from app.adapters.inbound.workers.exceptions import (
    DatabaseConnectionError, InvalidDataError, PermanentError,
    ProcessingError, ResourceNotFoundError, StorageError, TransientError,
)
```

Apply Pattern 1 to:
- `analyze_photo_task`
- `generate_description_task`
- `answer_question_task`
- `batch_analyze_task`
- `analyze_pending_photos`

#### google_photos_sync.py (Continue)
Apply Pattern 2 (External API) to remaining tasks:
- `refresh_photo_url_task`
- `fetch_google_photo_bytes_task`
- `import_picker_photos_task`
- `schedule_google_photos_sync`

#### connector_sync.py
Add imports:
```python
from sqlalchemy.exc import DBAPIError, OperationalError
from app.adapters.inbound.workers.exceptions import (
    DatabaseConnectionError, InvalidDataError, PermanentError,
    ResourceNotFoundError, StorageError, TransientError,
)
```

Apply Pattern 1 to:
- `sync_local_folder_task`
- `index_single_file_task`
- `handle_file_deleted_task`
- `handle_file_moved_task`

#### face_clustering.py
Add imports:
```python
from sqlalchemy.exc import DBAPIError, OperationalError
from app.adapters.inbound.workers.exceptions import (
    DatabaseConnectionError, InvalidDataError, PermanentError,
    ResourceNotFoundError, TransientError,
)
```

Apply Pattern 1 to:
- `cluster_faces_task`
- `update_clusters_task`
- `merge_clusters_task`

## Implementation Checklist

For each task:
- [ ] Add retry decorator with appropriate exceptions
- [ ] Wrap task body in try/except blocks
- [ ] Log permanent errors with exc_info=True
- [ ] Log transient errors with retry count
- [ ] Convert unexpected exceptions to PermanentError
- [ ] Include context in all log extra fields
- [ ] Test retry behavior

## Testing Commands

```bash
# Run a single task to test error handling
celery -A app.adapters.inbound.workers.celery_app call task.name --args='["test-id"]'

# Monitor task retries
celery -A app.adapters.inbound.workers.celery_app events

# Check task status
celery -A app.adapters.inbound.workers.celery_app inspect active
```

## Verification

After applying patterns, verify:
1. All tasks have retry decorators
2. All tasks log with structured context
3. Transient errors trigger retries
4. Permanent errors fail immediately
5. Unknown errors are logged and fail (converted to PermanentError)

## Exception Mapping Guide

| Error Scenario | Exception Type | Will Retry? |
|---------------|----------------|-------------|
| Photo not found | ResourceNotFoundError | No |
| Invalid UUID | InvalidDataError | No |
| File permission denied | StorageError | No |
| Network timeout | NetworkError | Yes (5x) |
| Database deadlock | DatabaseConnectionError | Yes (5x) |
| API rate limit | RateLimitError | Yes (5x, longer backoff) |
| Token expired | TokenRefreshError | Yes (1x) |
| OAuth missing | AuthenticationError | No |
| ML model OOM | TransientError | Yes (3x) |
| Corrupted image | ProcessingError | No |
| Qdrant timeout | TransientError | Yes (5x) |

## Quick Reference: Retry Configuration

- **Initial Delay**: 60 seconds
- **Max Retries**: 5 attempts
- **Backoff**: Exponential (60s, 120s, 240s, 480s, 600s)
- **Backoff Max**: 600 seconds (10 minutes)
- **Jitter**: Enabled (prevents thundering herd)
- **Acks Late**: Enabled (requeue on worker crash)

## Success Criteria

✅ All tasks have consistent error handling
✅ Transient failures retry automatically
✅ Permanent failures fail fast
✅ All errors logged with context
✅ Retry attempts tracked
✅ Production reliability improved significantly
