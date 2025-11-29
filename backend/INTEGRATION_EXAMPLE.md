# Circuit Breaker Fallback - Integration Example

This document shows how to integrate the circuit breaker fallback mechanism into your application services.

## 1. Basic Integration in PhotoProcessingService

### Before (Without Fallback)

```python
# Current implementation
async def process_photo(self, photo: Photo) -> None:
    """Process photo with embeddings."""
    # ... photo analysis code ...

    # Store embedding (may fail if Qdrant is down)
    await self.vector_store.store_photo_embedding(
        photo.id,
        embedding,
        payload={"filename": photo.filename}
    )
```

### After (With Fallback)

```python
from app.adapters.outbound.persistence.qdrant.fallback import QdrantFallbackQueue
from redis.asyncio import from_url

class PhotoProcessingService:
    def __init__(
        self,
        vector_store: QdrantVectorStore,
        photo_repo: PhotoRepository,
        ml_services: MLServices,
        file_storage: FileStorage,
        fallback_queue: QdrantFallbackQueue,  # Add fallback queue dependency
    ):
        self.vector_store = vector_store
        self.photo_repo = photo_repo
        self.ml_services = ml_services
        self.file_storage = file_storage
        self.fallback_queue = fallback_queue

    async def process_photo(self, photo: Photo) -> None:
        """Process photo with embeddings and fallback queueing."""
        # ... photo analysis code ...

        # Store embedding with fallback to queue
        await self._store_embedding_with_fallback(
            photo.id,
            embedding,
            payload={"filename": photo.filename}
        )

    async def _store_embedding_with_fallback(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Store embedding with automatic fallback to queue on failure."""
        try:
            await self.vector_store.store_photo_embedding(
                photo_id,
                embedding,
                payload=payload,
            )
            logger.debug(f"Stored embedding for photo {photo_id}")
        except Exception as e:
            logger.warning(
                f"Failed to store embedding, queuing for retry: {e}",
                extra={
                    "photo_id": str(photo_id),
                    "error_type": type(e).__name__,
                },
            )
            # Queue operation for later retry
            await self.fallback_queue.enqueue_embedding(
                operation="store_photo_embedding",
                photo_id=photo_id,
                embedding=embedding.to_list(),
                payload=payload,
            )
```

## 2. Dependency Injection Setup

### Update FastAPI Dependency Container

```python
# In app/adapters/inbound/api/dependencies.py or similar

from app.adapters.outbound.persistence.qdrant.fallback import QdrantFallbackQueue
from redis.asyncio import from_url

@lru_cache
def get_fallback_queue() -> QdrantFallbackQueue:
    """Get or create fallback queue instance."""
    redis_client = asyncio.run(
        from_url(get_settings().redis_url, decode_responses=True)
    )
    return QdrantFallbackQueue(redis_client)

async def get_photo_processing_service(
    session: AsyncSession = Depends(get_session),
    photo_repo: PhotoRepository = Depends(get_photo_repo),
    vector_store: VectorStore = Depends(get_vector_store),
    ml_services: MLServices = Depends(get_ml_services),
    file_storage: FileStorage = Depends(get_file_storage),
    fallback_queue: QdrantFallbackQueue = Depends(get_fallback_queue),  # Add dependency
) -> PhotoProcessingService:
    """Create PhotoProcessingService with all dependencies."""
    return PhotoProcessingService(
        vector_store=vector_store,
        photo_repo=photo_repo,
        ml_services=ml_services,
        file_storage=file_storage,
        fallback_queue=fallback_queue,  # Inject fallback queue
    )
```

## 3. Celery Beat Configuration

### Add to celery_app.py

```python
# In app/adapters/inbound/workers/celery_app.py

# Add to beat_schedule configuration
celery_app.conf.beat_schedule.update({
    "process-qdrant-fallback-queue": {
        "task": "app.adapters.inbound.workers.tasks.qdrant_recovery.process_qdrant_fallback_queue",
        "schedule": 300.0,  # Run every 5 minutes
        "options": {
            "queue": "default",
            "expires": 600,  # Task expires in 10 minutes
        }
    },
})
```

## 4. Worker Task Setup

### Register Task in Celery

The task is already registered via autodiscovery, but you can manually invoke it:

```python
# In any Celery task or background job

from app.adapters.inbound.workers.tasks.qdrant_recovery import (
    process_qdrant_fallback_queue,
)

# Trigger manually (e.g., after Qdrant recovers)
process_qdrant_fallback_queue.apply_async(queue="default")

# Or schedule for later
from celery import current_app
current_app.send_task(
    "app.adapters.inbound.workers.tasks.qdrant_recovery.process_qdrant_fallback_queue",
    countdown=60,  # Run in 60 seconds
)
```

## 5. Face Clustering Integration

```python
class FaceClusteringService:
    def __init__(
        self,
        vector_store: QdrantVectorStore,
        face_repo: FaceRepository,
        fallback_queue: QdrantFallbackQueue,  # Add dependency
    ):
        self.vector_store = vector_store
        self.face_repo = face_repo
        self.fallback_queue = fallback_queue

    async def update_face_embedding(
        self,
        face_id: UUID,
        embedding: Embedding,
        cluster_id: UUID | None = None,
    ) -> None:
        """Update face embedding with fallback."""
        payload = {}
        if cluster_id:
            payload["cluster_id"] = str(cluster_id)

        try:
            await self.vector_store.store_face_embedding(
                face_id,
                embedding,
                payload=payload,
            )
        except Exception as e:
            logger.warning(f"Face embedding failed, queueing: {e}")
            await self.fallback_queue.enqueue_embedding(
                operation="store_face_embedding",
                photo_id=face_id,  # face_id stored as photo_id
                embedding=embedding.to_list(),
                payload=payload,
            )
```

## 6. Monitoring Integration

### Add Health Check Endpoint

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/qdrant-queue")
async def check_qdrant_queue(
    fallback_queue: QdrantFallbackQueue = Depends(get_fallback_queue),
) -> dict[str, Any]:
    """Check status of Qdrant fallback queue."""
    try:
        queue_length = await fallback_queue.queue_length()

        return {
            "status": "healthy",
            "queue_length": queue_length,
            "pending_embeddings": queue_length,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Fallback queue unreachable: {e}",
        )
```

### Prometheus Metrics

```python
from prometheus_client import Gauge, Counter

# Define metrics
fallback_queue_length = Gauge(
    "qdrant_fallback_queue_length",
    "Number of pending embeddings in fallback queue",
)

fallback_queue_processed = Counter(
    "qdrant_fallback_queue_processed_total",
    "Total embeddings processed from fallback queue",
    ["operation", "status"],  # status: success, failed, requeued
)

# Update in recovery task callback
def on_recovery_task_complete(result: dict[str, int]) -> None:
    """Update metrics after recovery task completes."""
    fallback_queue_length.set(0)  # Reset after processing
    fallback_queue_processed.labels(
        operation="store_photo_embedding",
        status="success",
    ).inc(result.get("processed", 0))
    fallback_queue_processed.labels(
        operation="store_photo_embedding",
        status="requeued",
    ).inc(result.get("requeued", 0))
```

## 7. Error Handling in Application Layer

```python
from app.adapters.inbound.workers.exceptions import CircuitBreakerError

async def upload_photo_with_resilience(
    photo: Photo,
    vector_store: VectorStore,
    fallback_queue: QdrantFallbackQueue,
) -> dict[str, Any]:
    """Upload photo with resilient embedding storage."""

    # Upload photo file
    file_storage_result = await file_storage.store(photo)

    # Extract embedding
    embedding = await ml_services.extract_clip_embedding(photo)

    # Store with fallback
    try:
        await vector_store.store_photo_embedding(
            photo.id,
            embedding,
            payload={"filename": photo.filename, "size": photo.size},
        )
        return {
            "status": "success",
            "queued": False,
            "message": "Photo indexed immediately",
        }
    except CircuitBreakerError as e:
        # Circuit is open, queue for later
        await fallback_queue.enqueue_embedding(
            operation="store_photo_embedding",
            photo_id=photo.id,
            embedding=embedding.to_list(),
            payload={"filename": photo.filename},
        )
        return {
            "status": "partial",
            "queued": True,
            "message": "Photo uploaded, indexing queued (Qdrant unavailable)",
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

## 8. Testing Integration

### Unit Test with Mocked Queue

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_photo_processing_queues_on_vector_store_failure(
    photo_service: PhotoProcessingService,
    mock_vector_store: AsyncMock,
    mock_fallback_queue: AsyncMock,
) -> None:
    """Test that photos are queued when vector store fails."""

    # Setup: Vector store fails
    mock_vector_store.store_photo_embedding.side_effect = Exception("Connection timeout")

    photo = Photo(id=uuid4(), filename="test.jpg")
    embedding = Embedding.from_list([0.1, 0.2, 0.3])

    # Execute
    await photo_service._store_embedding_with_fallback(
        photo.id,
        embedding,
        payload={"filename": photo.filename},
    )

    # Verify: Fallback queue was called
    mock_fallback_queue.enqueue_embedding.assert_called_once()
    call_args = mock_fallback_queue.enqueue_embedding.call_args
    assert call_args.kwargs["operation"] == "store_photo_embedding"
    assert call_args.kwargs["photo_id"] == photo.id
    assert call_args.kwargs["embedding"] == embedding.to_list()
```

### Integration Test with Real Queue

```python
@pytest.mark.asyncio
async def test_recovery_task_processes_queued_embeddings(
    photo_service: PhotoProcessingService,
    fallback_queue: QdrantFallbackQueue,
    redis_client: Redis,
) -> None:
    """Test full cycle: enqueue, then process."""

    photo_id = uuid4()
    embedding = Embedding.from_list([0.1, 0.2, 0.3, 0.4, 0.5])
    payload = {"filename": "test.jpg"}

    # Enqueue operation
    await fallback_queue.enqueue_embedding(
        operation="store_photo_embedding",
        photo_id=photo_id,
        embedding=embedding.to_list(),
        payload=payload,
    )

    # Verify in queue
    queue_len = await fallback_queue.queue_length()
    assert queue_len == 1

    # Process queue
    from app.adapters.inbound.workers.tasks.qdrant_recovery import (
        _process_queue_async,
    )
    result = await _process_queue_async()

    # Verify processed
    assert result["processed"] == 1
    assert result["failed"] == 0
    assert result["requeued"] == 0

    # Verify empty
    queue_len = await fallback_queue.queue_length()
    assert queue_len == 0
```

## 9. Graceful Degradation Scenarios

### Scenario 1: Temporary Qdrant Outage

```
1. API receives photo upload
2. Vector store raises exception (circuit not yet open)
3. Fallback queue catches exception
4. Operation enqueued to Redis
5. Response to client: "Photo uploaded, indexing queued"
6. Qdrant recovers (circuit breaker half-open)
7. Recovery task processes queue periodically
8. Embeddings are stored successfully
```

### Scenario 2: Extended Qdrant Outage

```
1. Multiple photo uploads during outage
2. All enqueued to fallback queue
3. Circuit breaker opens after 5 failures
4. Subsequent requests immediately queue
5. Qdrant remains down for hours
6. Queue accumulates 10,000+ embeddings
7. Qdrant recovers
8. Recovery task processes backlog at 2,000 embeddings/min
9. Backlog cleared in 5 minutes
```

### Scenario 3: Transient Failures

```
1. First upload fails → queued
2. Recovery task processes after 5 minutes
3. Transient network issue, task fails
4. Task re-queued with retry_count=1
5. Next recovery cycle retries
6. Success → embedding stored
```

## 10. Production Rollout Checklist

- [ ] Configure Celery Beat schedule
- [ ] Test with real Qdrant instance
- [ ] Load test to verify throughput
- [ ] Configure monitoring/alerting
- [ ] Add health check endpoint
- [ ] Document for ops team
- [ ] Plan for queue cleanup procedures
- [ ] Set up DLQ for investigation
- [ ] Test manual recovery triggering
- [ ] Train team on queue monitoring

This integration provides resilient embedding operations while maintaining full transparency to the application layer about availability status.
