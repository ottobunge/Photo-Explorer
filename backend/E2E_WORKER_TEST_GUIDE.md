# End-to-End Tests with Celery Worker

## Overview

This guide explains the E2E test infrastructure for testing asynchronous photo processing with Celery workers.

## Architecture

The E2E test infrastructure adds support for running Celery worker tasks during tests:

### 1. **Celery Worker Fixture** (`tests/e2e/conftest.py`)

```python
@pytest.fixture(scope="session", autouse=True)
def celery_worker(celery_app_for_e2e: Celery) -> None:
    """Start and stop Celery worker for entire E2E test session."""
```

- Starts a Celery worker in a background thread at the session scope
- Automatically starts before any E2E tests run
- Automatically stops after all tests complete
- Uses thread pool (not fork) to avoid issues with pytest fixtures

### 2. **Task Completion Helpers** (`tests/e2e/conftest.py`)

```python
def wait_for_celery_task(
    task_id: str,
    expected_state: str = "SUCCESS",
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> AsyncResult:
    """Wait for a Celery task to reach expected state."""

async def wait_for_celery_task_async(
    task_id: str,
    expected_state: str = "SUCCESS",
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> AsyncResult:
    """Async version of wait_for_celery_task."""
```

These helpers allow tests to:
- Enqueue async tasks
- Wait for tasks to complete
- Verify task success or failure
- Get result data from tasks

## Running E2E Tests

### Start a Single Test

```bash
cd backend
poetry run pytest tests/e2e/test_async_photo_processing.py::TestAsyncPhotoProcessing::test_photo_processing_task_completes -xvs
```

### Run All E2E Tests

```bash
poetry run pytest tests/e2e/ -xvs
```

### Run Only Worker Tests

```bash
poetry run pytest tests/e2e/test_async_photo_processing.py -xvs
```

## Test Structure

### Example Test Pattern

```python
import pytest
from app.adapters.inbound.workers.celery_app import celery_app
from tests.e2e.conftest import wait_for_celery_task

@pytest.mark.asyncio
class TestWorkerProcessing:
    async def test_something(self, celery_worker):
        """Test that uses the worker fixture."""
        # The celery_worker fixture is autouse,
        # but we include it here for clarity

        # 1. Set up test data
        photo = Photo.create(filename="test.jpg")
        await repo.save(photo)

        # 2. Enqueue a task
        task = celery_app.send_task(
            "photo_processing.process_photo",
            args=[str(photo.id.value)],
            queue="processing",
        )

        # 3. Wait for task to complete
        result = wait_for_celery_task(
            task.id,
            expected_state="SUCCESS",
            timeout=60.0,
        )

        assert result.successful()

        # 4. Verify results
        processed_photo = await repo.find_by_id(photo.id.value)
        assert processed_photo.thumbnail_path is not None
```

## Available Tasks

The worker supports all tasks from `app/adapters/inbound/workers/tasks/`:

### Photo Processing Tasks
- `photo_processing.process_photo` - Main processing pipeline
- `photo_processing.detect_faces` - Face detection only
- `photo_processing.generate_embedding_from_thumbnail` - CLIP embedding

### Face Clustering Tasks
- `face_clustering.cluster_faces` - Cluster detected faces
- `face_clustering.update_clusters` - Update existing clusters
- `face_clustering.merge_clusters` - Merge face clusters

### Other Tasks
- `batch_operations.cleanup_orphans` - Clean up orphaned files
- `connector_sync.*` - Connector sync tasks
- `google_photos_sync.*` - Google Photos sync tasks

## Task Queues

Tasks are routed to specific queues:

| Task Pattern | Queue | Purpose |
|---|---|---|
| `photo_processing.*` | `processing` | Photo analysis and thumbnail generation |
| `face_clustering.*` | `clustering` | Face clustering operations |
| `connector_sync.*` | `sync` | Connector synchronization |
| Others | `default` | General tasks |

## Timeout Configuration

Worker timeouts are configured in `app/adapters/inbound/workers/celery_app.py`:

```python
task_soft_time_limit=1500,    # 25 minutes soft limit
task_time_limit=1800,         # 30 minutes hard limit
```

Tests should use appropriately shorter timeouts:

```python
# For simple tests (should complete in < 10s)
wait_for_celery_task(task.id, timeout=30.0)

# For processing tests (may take 1-2 min)
wait_for_celery_task(task.id, timeout=120.0)

# For complex tests (may take several minutes)
wait_for_celery_task(task.id, timeout=300.0)
```

## Troubleshooting

### Test Hangs

If a test hangs:

1. **Check worker is running**: Look for log message "Celery worker is ready to accept tasks"
2. **Check timeout value**: Increase `timeout` parameter in `wait_for_celery_task()`
3. **Check for task errors**: Add logging to see task failures

### Task Failures

If a task fails:

1. **Check error message**: The result contains the exception
2. **Check test infrastructure**: Ensure PostgreSQL, Redis, Qdrant are running
3. **Check dependencies**: ML services need to be initialized

### Signal Handler Errors

You may see: `ValueError: signal only works in main thread`

This is a warning from the worker initialization in thread context. It's harmless - the worker still starts and processes tasks successfully.

## Performance Considerations

- Worker runs in a single thread (not multi-process) for test stability
- Each E2E test session starts the worker once (session scope)
- Tests share the same worker instance
- Concurrent tests can run against the worker

## Test Isolation

- Tests use `test_session` fixture for database isolation
- Each test gets a fresh database transaction
- File storage is isolated per test
- Worker tasks write to shared test database

## Implementation Details

### Worker Startup (`conftest.py`)

```python
class TestCeleryWorker:
    def start(self) -> None:
        """Start worker in background thread."""
        self.celery_app.Worker(
            concurrency=2,
            pool="threads",  # Thread pool, not fork
            queues=["default", "processing", "clustering", "dlq"],
        )
```

### Task Polling

```python
def wait_for_celery_task(task_id, expected_state="SUCCESS", timeout=30):
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Task {task_id} did not complete")

        result = celery_app.AsyncResult(task_id)
        if result.state == expected_state:
            return result

        time.sleep(0.5)  # Poll every 500ms
```

## Next Steps

- Implement more E2E tests for other workflows
- Add integration with CI/CD pipeline
- Monitor test performance and optimize timeouts
- Consider parallelizing independent tests
