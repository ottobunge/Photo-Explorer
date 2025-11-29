"""Queue for failed Qdrant operations with circuit breaker fallback."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Union
from uuid import UUID

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class QdrantFallbackQueue:
    """Queue for failed Qdrant operations.

    When the Qdrant circuit breaker is open (service unavailable),
    embedding operations are queued to Redis. A Celery task periodically
    processes these queued operations when the service recovers.
    """

    def __init__(self, redis_client: Redis) -> None:  # type: ignore[type-arg]
        """Initialize the fallback queue.

        Args:
            redis_client: Redis client instance for queue storage
        """
        self._redis = redis_client
        self._queue_key = "qdrant:fallback_queue"

    async def enqueue_embedding(
        self,
        operation: str,
        photo_id: UUID,
        embedding: list[float],
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Queue embedding operation for retry.

        Args:
            operation: Type of operation ('store_photo_embedding' or 'store_face_embedding')
            photo_id: UUID of the photo or face being stored
            embedding: Vector embedding as list of floats
            payload: Optional metadata to store with embedding

        Raises:
            Exception: If Redis enqueue fails
        """
        task: dict[str, Any] = {
            "operation": operation,
            "photo_id": str(photo_id),
            "embedding": embedding,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
        }
        await self._redis.rpush(self._queue_key, json.dumps(task))  # type: ignore[return-value]
        queue_len = await self.queue_length()
        logger.info(
            f"Queued {operation} for photo {photo_id}",
            extra={"queue_length": queue_len},
        )

    async def queue_length(self) -> int:
        """Get current queue length.

        Returns:
            Number of tasks in the fallback queue

        Raises:
            Exception: If Redis operation fails
        """
        result: Union[int, Any] = await self._redis.llen(self._queue_key)  # type: ignore[assignment]
        return int(result)

    async def dequeue_batch(self, batch_size: int = 100) -> list[dict[str, Any]]:
        """Get batch of queued tasks.

        Retrieves up to batch_size tasks from the front of the queue.
        Tasks are removed from the queue (LPOP operation).

        Args:
            batch_size: Maximum number of tasks to retrieve

        Returns:
            List of task dictionaries with operation details

        Raises:
            Exception: If Redis operation fails
        """
        tasks: list[dict[str, Any]] = []
        for _ in range(batch_size):
            task_json: Union[str, list, None, Any] = await self._redis.lpop(self._queue_key)  # type: ignore[assignment]
            if task_json is None:
                break
            tasks.append(json.loads(task_json))
        return tasks

    async def requeue_with_retry(self, task: dict[str, Any]) -> None:
        """Re-queue a task with incremented retry count.

        Called when a queued task fails to process. The task is re-queued
        with an updated retry count and timestamp for the next retry attempt.

        Args:
            task: Task dictionary to re-queue

        Raises:
            Exception: If Redis operation fails
        """
        task["retry_count"] = task.get("retry_count", 0) + 1
        task["timestamp"] = datetime.now(timezone.utc).isoformat()
        await self._redis.rpush(self._queue_key, json.dumps(task))  # type: ignore[return-value]
        logger.warning(
            f"Re-queued {task['operation']} (attempt {task['retry_count']})",
            extra={"retry_count": task["retry_count"]},
        )
