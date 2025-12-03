# Qdrant Fallback Strategy - Code Examples

## Core Implementation Snippets

### 1. Vector Store with Fallback (store_photo_embedding)

```python
# File: /app/adapters/outbound/persistence/qdrant/vector_store.py

async def _store_photo_embedding_impl(
    self,
    photo_id: UUID,
    embedding: Embedding,
    payload: Optional[dict] = None,
) -> None:
    """Internal implementation with circuit breaker protection."""
    point = qdrant_models.PointStruct(
        id=str(photo_id),
        vector=embedding.to_list(),
        payload=payload or {},
    )
    await self._client.upsert(
        collection_name=self._photos_collection,
        points=[point],
    )
    logger.debug(f"Stored embedding for photo {photo_id}")


@log_circuit_breaker_events
@monitor_circuit_breaker("store_photo_embedding")
@circuit(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
)
async def _store_photo_embedding_circuit_breaker(
    self,
    photo_id: UUID,
    embedding: Embedding,
    payload: Optional[dict] = None,
) -> None:
    """Protected by circuit breaker."""
    await self._store_photo_embedding_impl(photo_id, embedding, payload)


async def store_photo_embedding(
    self,
    photo_id: UUID,
    embedding: Embedding,
    payload: Optional[dict] = None,
) -> None:
    """Store with fallback to queue on failure."""
    try:
        await self._store_photo_embedding_circuit_breaker(
            photo_id, embedding, payload
        )
    except Exception as e:
        # Circuit breaker is open - queue the operation
        if self._fallback_queue is not None:
            logger.info(
                f"Qdrant unavailable - queuing photo embedding",
                extra={
                    "photo_id": str(photo_id),
                    "error": str(e)[:100],
                    "error_type": type(e).__name__,
                },
            )
            await self._fallback_queue.enqueue_embedding(
                operation="store_photo_embedding",
                photo_id=photo_id,
                embedding=embedding.to_list(),
                payload=payload,
            )
        else:
            # No fallback queue configured - log warning
            logger.warning(
                f"Qdrant unavailable and no fallback queue configured",
                extra={
                    "photo_id": str(photo_id),
                    "error": str(e)[:100],
                },
            )
```

### 2. Fallback Queue Implementation

```python
# File: /app/adapters/outbound/persistence/qdrant/fallback.py

class QdrantFallbackQueue:
    """Queue for failed Qdrant operations."""

    def __init__(self, redis_client: Redis) -> None:
        """Initialize with Redis client."""
        self._redis = redis_client
        self._queue_key = "qdrant:fallback_queue"

    async def enqueue_embedding(
        self,
        operation: str,
        photo_id: UUID,
        embedding: list[float],
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Queue operation for retry."""
        task: dict[str, Any] = {
            "operation": operation,
            "photo_id": str(photo_id),
            "embedding": embedding,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
        }
        await self._redis.rpush(self._queue_key, json.dumps(task))
        queue_len = await self.queue_length()
        logger.info(
            f"Queued {operation} for photo {photo_id}",
            extra={"queue_length": queue_len},
        )

        # Record metrics
        fallback_queue_enqueued_total.labels(operation_type=operation).inc()
        fallback_queue_length_metric.set(queue_len)

    async def queue_length(self) -> int:
        """Get current queue length."""
        result: Union[int, Any] = await self._redis.llen(self._queue_key)
        return int(result)

    async def dequeue_batch(self, batch_size: int = 100) -> list[dict[str, Any]]:
        """Retrieve batch of queued tasks."""
        tasks: list[dict[str, Any]] = []
        for _ in range(batch_size):
            task_json: Union[str, list, None, Any] = await self._redis.lpop(
                self._queue_key
            )
            if task_json is None:
                break
            tasks.append(json.loads(task_json))
        return tasks

    async def requeue_with_retry(self, task: dict[str, Any]) -> None:
        """Re-queue with incremented retry count."""
        task["retry_count"] = task.get("retry_count", 0) + 1
        task["timestamp"] = datetime.now(timezone.utc).isoformat()
        await self._redis.rpush(self._queue_key, json.dumps(task))
        logger.warning(
            f"Re-queued {task['operation']} (attempt {task['retry_count']})",
            extra={"retry_count": task["retry_count"]},
        )

        # Record metrics
        fallback_queue_requeued_total.labels(
            operation_type=task["operation"]
        ).inc()
        queue_len = await self.queue_length()
        fallback_queue_length_metric.set(queue_len)
```

### 3. Recovery Task

```python
# File: /app/adapters/inbound/workers/tasks/qdrant_recovery.py

MAX_RETRIES_PER_TASK = 3
BATCH_SIZE = 100


@celery_app.task(
    name="app.adapters.inbound.workers.tasks.qdrant_recovery.process_qdrant_fallback_queue",
    bind=True,
)
def process_qdrant_fallback_queue(self: Any) -> dict[str, int]:
    """Process queued Qdrant operations when service recovers."""
    try:
        result = asyncio.run(_process_queue_async())
        logger.info(
            "Fallback queue processing completed",
            extra=result,
        )
        return result
    except Exception as e:
        logger.error(
            "Error processing fallback queue",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise


async def _process_queue_async() -> dict[str, int]:
    """Async implementation of queue processing."""
    settings = get_settings()
    redis_client = await from_url(settings.redis_url, decode_responses=True)
    start_time = time.time()

    try:
        queue = QdrantFallbackQueue(redis_client)
        vector_store = QdrantVectorStore()

        queue_length = await queue.queue_length()
        fallback_queue_length_metric.set(queue_length)

        if queue_length == 0:
            logger.debug("No queued Qdrant operations to process")
            return {
                "processed": 0,
                "failed": 0,
                "requeued": 0,
            }

        logger.info(
            f"Processing {queue_length} queued Qdrant operations",
            extra={"queue_length": queue_length},
        )

        processed = 0
        failed = 0
        requeued = 0

        # Process in batches
        while processed + failed + requeued < queue_length:
            tasks = await queue.dequeue_batch(BATCH_SIZE)
            if not tasks:
                break

            for task in tasks:
                try:
                    if task["operation"] == "store_photo_embedding":
                        await _process_photo_embedding(vector_store, task)
                        processed += 1
                        fallback_queue_processed_total.labels(
                            operation_type="store_photo_embedding"
                        ).inc()

                    elif task["operation"] == "store_face_embedding":
                        await _process_face_embedding(vector_store, task)
                        processed += 1
                        fallback_queue_processed_total.labels(
                            operation_type="store_face_embedding"
                        ).inc()

                    else:
                        logger.warning(
                            f"Unknown operation: {task['operation']}",
                            extra={"operation": task["operation"]},
                        )
                        failed += 1
                        fallback_queue_failed_total.labels(
                            operation_type=task.get("operation", "unknown")
                        ).inc()

                except Exception as e:
                    operation_type = task.get("operation", "unknown")
                    logger.error(
                        f"Failed to process queued task: {e}",
                        extra={
                            "operation": operation_type,
                            "retry_count": task.get("retry_count", 0),
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                        exc_info=True,
                    )
                    failed += 1
                    fallback_queue_failed_total.labels(
                        operation_type=operation_type
                    ).inc()

                    # Re-queue with retry count
                    if task.get("retry_count", 0) < MAX_RETRIES_PER_TASK:
                        await queue.requeue_with_retry(task)
                        requeued += 1

        logger.info(
            "Fallback queue processing completed",
            extra={
                "processed": processed,
                "failed": failed,
                "requeued": requeued,
            },
        )

        # Record final queue length and processing duration
        final_queue_length = await queue.queue_length()
        fallback_queue_length_metric.set(final_queue_length)
        duration = time.time() - start_time
        fallback_queue_recovery_duration.observe(duration)

        return {
            "processed": processed,
            "failed": failed,
            "requeued": requeued,
        }

    finally:
        await redis_client.close()


async def _process_photo_embedding(
    vector_store: QdrantVectorStore,
    task: dict[str, Any],
) -> None:
    """Process a queued photo embedding operation."""
    photo_id = UUID(task["photo_id"])
    embedding = Embedding.from_list(task["embedding"])
    payload = task.get("payload")

    await vector_store.store_photo_embedding(
        photo_id,
        embedding,
        payload,
    )

    logger.debug(
        f"Processed queued photo embedding for {photo_id}",
        extra={"photo_id": str(photo_id)},
    )


async def _process_face_embedding(
    vector_store: QdrantVectorStore,
    task: dict[str, Any],
) -> None:
    """Process a queued face embedding operation."""
    face_id = UUID(task["photo_id"])
    embedding = Embedding.from_list(task["embedding"])
    payload = task.get("payload")

    await vector_store.store_face_embedding(
        face_id,
        embedding,
        payload,
    )

    logger.debug(
        f"Processed queued face embedding for {face_id}",
        extra={"face_id": str(face_id)},
    )
```

### 4. Celery Beat Configuration

```python
# File: /app/adapters/inbound/workers/celery_app.py

celery_app.conf.update(
    # ... other config ...
    beat_schedule={
        "cleanup-orphaned-files": {
            "task": "app.adapters.inbound.workers.tasks.batch_operations.cleanup_orphans_task",
            "schedule": CLEANUP_ORPHANS_INTERVAL_SECONDS,
        },
        "monitor-db-pool": {
            "task": "monitoring.monitor_db_pool",
            "schedule": MONITOR_DB_POOL_INTERVAL_SECONDS,
        },
        "process-qdrant-fallback-queue": {
            "task": "app.adapters.inbound.workers.tasks.qdrant_recovery.process_qdrant_fallback_queue",
            "schedule": 300.0,  # Run every 5 minutes
        },
    },
)
```

### 5. Prometheus Metrics

```python
# File: /app/infrastructure/monitoring/circuit_breaker.py

# Fallback Queue Metrics

# Gauge: Current size of Qdrant fallback queue
fallback_queue_length = Gauge(
    "qdrant_fallback_queue_length",
    "Current number of operations in Qdrant fallback queue",
)

# Counter: Total operations queued to fallback
fallback_queue_enqueued_total = Counter(
    "qdrant_fallback_queue_enqueued_total",
    "Total operations enqueued to Qdrant fallback queue",
    ["operation_type"],
)

# Counter: Total operations successfully processed from fallback queue
fallback_queue_processed_total = Counter(
    "qdrant_fallback_queue_processed_total",
    "Total operations successfully processed from Qdrant fallback queue",
    ["operation_type"],
)

# Counter: Total operations that failed to process from fallback queue
fallback_queue_failed_total = Counter(
    "qdrant_fallback_queue_failed_total",
    "Total operations that failed to process from Qdrant fallback queue",
    ["operation_type"],
)

# Counter: Total operations requeued for retry
fallback_queue_requeued_total = Counter(
    "qdrant_fallback_queue_requeued_total",
    "Total operations requeued for retry from Qdrant fallback queue",
    ["operation_type"],
)

# Histogram: Recovery task execution time
fallback_queue_recovery_duration = Histogram(
    "qdrant_fallback_queue_recovery_duration_seconds",
    "Time to process Qdrant fallback queue batch in seconds",
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)
```

## Usage Examples

### Manual Testing - Enqueue Operation

```python
from redis.asyncio import from_url
from app.adapters.outbound.persistence.qdrant.fallback import QdrantFallbackQueue
from uuid import uuid4

async def test_enqueue():
    redis_client = await from_url("redis://localhost:6379", decode_responses=True)
    queue = QdrantFallbackQueue(redis_client)

    photo_id = uuid4()
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    payload = {"filename": "test.jpg"}

    await queue.enqueue_embedding(
        operation="store_photo_embedding",
        photo_id=photo_id,
        embedding=embedding,
        payload=payload,
    )

    length = await queue.queue_length()
    print(f"Queue length: {length}")

    await redis_client.close()
```

### Manual Testing - Process Queue

```python
from app.adapters.inbound.workers.tasks.qdrant_recovery import (
    process_qdrant_fallback_queue,
)

# Trigger recovery task manually
result = process_qdrant_fallback_queue()
print(f"Processed: {result['processed']}, Failed: {result['failed']}, Requeued: {result['requeued']}")
```

### Check Metrics via Prometheus

```bash
# Queue length
curl http://localhost:8000/metrics | grep qdrant_fallback_queue_length

# Enqueue rate (ops/sec over last 1 minute)
curl 'http://localhost:9090/api/v1/query?query=rate(qdrant_fallback_queue_enqueued_total%5B1m%5D)'

# Success rate
curl 'http://localhost:9090/api/v1/query?query=rate(qdrant_fallback_queue_processed_total%5B5m%5D)/(rate(qdrant_fallback_queue_processed_total%5B5m%5D)+rate(qdrant_fallback_queue_failed_total%5B5m%5D))'

# Recovery duration p95
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,qdrant_fallback_queue_recovery_duration_seconds_bucket)'
```

## Task Structure in Queue

```json
{
    "operation": "store_photo_embedding",
    "photo_id": "550e8400-e29b-41d4-a716-446655440000",
    "embedding": [
        0.1, 0.2, 0.3, 0.4, 0.5,
        // ... 508 more dimensions for CLIP embeddings
    ],
    "payload": {
        "filename": "photo.jpg",
        "cluster_id": "cluster-123",
        "other_metadata": "..."
    },
    "timestamp": "2024-12-01T12:00:00Z",
    "retry_count": 0
}
```

## Error Handling Pattern

```python
# Pattern used in vector_store.py

try:
    # Try direct operation
    await self._store_photo_embedding_circuit_breaker(photo_id, embedding, payload)
except Exception as e:
    # Graceful fallback
    if self._fallback_queue is not None:
        # Queue for later
        await self._fallback_queue.enqueue_embedding(
            operation="store_photo_embedding",
            photo_id=photo_id,
            embedding=embedding.to_list(),
            payload=payload,
        )
    else:
        # Log warning if queue not configured
        logger.warning("Fallback queue not available")
    # Don't re-raise - operation "succeeds" by queueing
```

## Monitoring Pattern

```python
# Record metrics at key points

# 1. On enqueue
fallback_queue_enqueued_total.labels(operation_type=operation).inc()
fallback_queue_length_metric.set(queue_len)

# 2. On successful process
fallback_queue_processed_total.labels(operation_type=operation).inc()

# 3. On failure
fallback_queue_failed_total.labels(operation_type=operation).inc()

# 4. On re-queue
fallback_queue_requeued_total.labels(operation_type=operation).inc()

# 5. On recovery completion
duration = time.time() - start_time
fallback_queue_recovery_duration.observe(duration)
```

## References

- Full documentation: `QDRANT_FALLBACK_STRATEGY.md`
- Quick reference: `QDRANT_FALLBACK_QUICK_REFERENCE.md`
- Implementation summary: `IMPLEMENTATION_SUMMARY_QDRANT_FALLBACK.md`
- Tests: `tests/unit/adapters/outbound/persistence/qdrant/test_fallback.py`
- Tests: `tests/unit/adapters/inbound/workers/tasks/test_qdrant_recovery.py`
