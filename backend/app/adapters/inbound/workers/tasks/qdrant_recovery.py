"""Celery task for recovering queued Qdrant operations."""

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from redis.asyncio import from_url

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.outbound.persistence.qdrant.fallback import QdrantFallbackQueue
from app.adapters.outbound.persistence.qdrant.vector_store import QdrantVectorStore
from app.config import get_settings
from app.domain.value_objects import Embedding
from app.infrastructure.monitoring.circuit_breaker import (
    fallback_queue_failed_total,
    fallback_queue_length as fallback_queue_length_metric,
    fallback_queue_processed_total,
    fallback_queue_recovery_duration,
)

logger = logging.getLogger(__name__)

# Configuration for recovery processing
MAX_RETRIES_PER_TASK = 3
BATCH_SIZE = 100


@celery_app.task(
    name="app.adapters.inbound.workers.tasks.qdrant_recovery.process_qdrant_fallback_queue",
    bind=True,
)
def process_qdrant_fallback_queue(self: Any) -> dict[str, int]:
    """Process queued Qdrant operations when service recovers.

    This Celery task runs periodically (e.g., every 5 minutes) to retry
    operations that were queued when the circuit breaker was open.

    Args:
        self: Celery task instance for retry handling

    Returns:
        Dictionary with processing statistics:
            - processed: Number of successfully processed tasks
            - failed: Number of tasks that failed
            - requeued: Number of tasks re-queued for retry

    Raises:
        Exception: If critical errors occur (logged and re-raised)
    """
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
    """Async implementation of queue processing.

    Connects to Redis and Qdrant, processes batches of queued operations,
    and tracks statistics for monitoring.

    Returns:
        Dictionary with processing statistics

    Raises:
        Exception: If Redis or Qdrant operations fail
    """
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
                        fallback_queue_processed_total.labels(operation_type="store_photo_embedding").inc()

                    elif task["operation"] == "store_face_embedding":
                        await _process_face_embedding(vector_store, task)
                        processed += 1
                        fallback_queue_processed_total.labels(operation_type="store_face_embedding").inc()

                    else:
                        logger.warning(
                            f"Unknown operation: {task['operation']}",
                            extra={"operation": task["operation"]},
                        )
                        failed += 1
                        fallback_queue_failed_total.labels(operation_type=task.get("operation", "unknown")).inc()

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
                    fallback_queue_failed_total.labels(operation_type=operation_type).inc()

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
    """Process a queued photo embedding operation.

    Args:
        vector_store: Qdrant vector store instance
        task: Task dictionary with operation details

    Raises:
        Exception: If embedding storage fails
    """
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
    """Process a queued face embedding operation.

    Args:
        vector_store: Qdrant vector store instance
        task: Task dictionary with operation details

    Raises:
        Exception: If embedding storage fails
    """
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
