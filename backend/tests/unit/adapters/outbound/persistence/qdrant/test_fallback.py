"""Tests for Qdrant fallback queue."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.qdrant.fallback import QdrantFallbackQueue
from app.domain.value_objects import Embedding


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    return AsyncMock()


@pytest.fixture
def fallback_queue(mock_redis):
    """Create a QdrantFallbackQueue instance with mock Redis."""
    return QdrantFallbackQueue(mock_redis)


@pytest.mark.asyncio
async def test_enqueue_embedding_stores_task_in_redis(fallback_queue, mock_redis):
    """Test that enqueue_embedding stores task in Redis."""
    photo_id = uuid4()
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    payload = {"filename": "test.jpg"}

    # Mock Redis methods
    mock_redis.rpush = AsyncMock(return_value=1)
    mock_redis.llen = AsyncMock(return_value=1)

    await fallback_queue.enqueue_embedding(
        operation="store_photo_embedding",
        photo_id=photo_id,
        embedding=embedding,
        payload=payload,
    )

    # Verify rpush was called
    assert mock_redis.rpush.called
    call_args = mock_redis.rpush.call_args
    assert call_args[0][0] == "qdrant:fallback_queue"

    # Verify task data
    task_json = call_args[0][1]
    task = json.loads(task_json)
    assert task["operation"] == "store_photo_embedding"
    assert task["photo_id"] == str(photo_id)
    assert task["embedding"] == embedding
    assert task["payload"] == payload
    assert task["retry_count"] == 0
    assert "timestamp" in task


@pytest.mark.asyncio
async def test_enqueue_embedding_without_payload(fallback_queue, mock_redis):
    """Test enqueue_embedding with optional payload omitted."""
    photo_id = uuid4()
    embedding = [0.1, 0.2]

    mock_redis.rpush = AsyncMock(return_value=1)
    mock_redis.llen = AsyncMock(return_value=1)

    await fallback_queue.enqueue_embedding(
        operation="store_face_embedding",
        photo_id=photo_id,
        embedding=embedding,
    )

    call_args = mock_redis.rpush.call_args
    task_json = call_args[0][1]
    task = json.loads(task_json)

    assert task["payload"] is None
    assert task["retry_count"] == 0


@pytest.mark.asyncio
async def test_queue_length_returns_redis_count(fallback_queue, mock_redis):
    """Test that queue_length returns the Redis list length."""
    mock_redis.llen = AsyncMock(return_value=42)

    length = await fallback_queue.queue_length()

    assert length == 42
    mock_redis.llen.assert_called_once_with("qdrant:fallback_queue")


@pytest.mark.asyncio
async def test_dequeue_batch_returns_tasks(fallback_queue, mock_redis):
    """Test that dequeue_batch retrieves and parses tasks."""
    task1 = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }
    task2 = {
        "operation": "store_face_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.3, 0.4],
        "payload": {"cluster_id": "cluster1"},
        "retry_count": 1,
        "timestamp": "2024-01-01T00:01:00",
    }

    # Mock lpop to return tasks, then None
    mock_redis.lpop = AsyncMock(side_effect=[
        json.dumps(task1),
        json.dumps(task2),
        None,
    ])

    tasks = await fallback_queue.dequeue_batch(batch_size=100)

    assert len(tasks) == 2
    assert tasks[0] == task1
    assert tasks[1] == task2
    assert mock_redis.lpop.call_count == 3  # Called 3 times (2 tasks + 1 None)


@pytest.mark.asyncio
async def test_dequeue_batch_respects_batch_size(fallback_queue, mock_redis):
    """Test that dequeue_batch respects the batch_size parameter."""
    task_count = 5
    tasks = [
        {
            "operation": "store_photo_embedding",
            "photo_id": str(uuid4()),
            "embedding": [0.1],
            "payload": None,
            "retry_count": 0,
            "timestamp": "2024-01-01T00:00:00",
        }
        for _ in range(task_count)
    ]

    # Mock lpop to return 3 tasks
    mock_redis.lpop = AsyncMock(side_effect=[
        json.dumps(tasks[0]),
        json.dumps(tasks[1]),
        json.dumps(tasks[2]),
    ])

    result = await fallback_queue.dequeue_batch(batch_size=3)

    assert len(result) == 3
    assert mock_redis.lpop.call_count == 3


@pytest.mark.asyncio
async def test_dequeue_batch_empty_queue(fallback_queue, mock_redis):
    """Test dequeue_batch with empty queue."""
    mock_redis.lpop = AsyncMock(return_value=None)

    tasks = await fallback_queue.dequeue_batch(batch_size=100)

    assert tasks == []
    mock_redis.lpop.assert_called_once()


@pytest.mark.asyncio
async def test_requeue_with_retry_increments_retry_count(fallback_queue, mock_redis):
    """Test that requeue_with_retry increments retry count."""
    original_task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 2,
        "timestamp": "2024-01-01T00:00:00",
    }

    mock_redis.rpush = AsyncMock(return_value=1)

    await fallback_queue.requeue_with_retry(original_task)

    # Verify rpush was called
    assert mock_redis.rpush.called
    call_args = mock_redis.rpush.call_args
    task_json = call_args[0][1]
    task = json.loads(task_json)

    assert task["retry_count"] == 3
    assert task["operation"] == "store_photo_embedding"
    assert "timestamp" in task


@pytest.mark.asyncio
async def test_requeue_with_retry_updates_timestamp(fallback_queue, mock_redis):
    """Test that requeue_with_retry updates the timestamp."""
    original_task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }
    original_timestamp = original_task["timestamp"]

    mock_redis.rpush = AsyncMock(return_value=1)

    await fallback_queue.requeue_with_retry(original_task)

    call_args = mock_redis.rpush.call_args
    task_json = call_args[0][1]
    task = json.loads(task_json)

    # Timestamp should be updated
    assert task["timestamp"] != original_timestamp
    assert "T" in task["timestamp"]  # ISO format check


@pytest.mark.asyncio
async def test_requeue_with_retry_handles_missing_retry_count(fallback_queue, mock_redis):
    """Test requeue_with_retry with task missing retry_count."""
    task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "payload": None,
        "timestamp": "2024-01-01T00:00:00",
        # Note: no retry_count
    }

    mock_redis.rpush = AsyncMock(return_value=1)

    await fallback_queue.requeue_with_retry(task)

    call_args = mock_redis.rpush.call_args
    task_json = call_args[0][1]
    requeued_task = json.loads(task_json)

    # Should default to 0 and increment to 1
    assert requeued_task["retry_count"] == 1


@pytest.mark.asyncio
async def test_multiple_enqueue_operations(fallback_queue, mock_redis):
    """Test multiple enqueue operations in sequence."""
    photo_ids = [uuid4() for _ in range(3)]
    embeddings = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
        [0.7, 0.8, 0.9],
    ]

    mock_redis.rpush = AsyncMock(return_value=1)
    mock_redis.llen = AsyncMock(side_effect=[1, 2, 3])

    for photo_id, embedding in zip(photo_ids, embeddings):
        await fallback_queue.enqueue_embedding(
            operation="store_photo_embedding",
            photo_id=photo_id,
            embedding=embedding,
        )

    # Verify all operations were queued
    assert mock_redis.rpush.call_count == 3
    assert mock_redis.llen.call_count == 3


@pytest.mark.asyncio
async def test_dequeue_batch_with_malformed_json(fallback_queue, mock_redis):
    """Test dequeue_batch handles malformed JSON gracefully."""
    valid_task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    # Mock lpop to return valid task then malformed JSON
    mock_redis.lpop = AsyncMock(side_effect=[
        json.dumps(valid_task),
        "{malformed json}",  # This will raise JSONDecodeError
        None,
    ])

    # Should raise exception on malformed JSON
    with pytest.raises(json.JSONDecodeError):
        await fallback_queue.dequeue_batch(batch_size=100)


@pytest.mark.asyncio
async def test_queue_key_isolation(fallback_queue, mock_redis):
    """Test that each queue uses its own Redis key."""
    photo_id = uuid4()
    embedding = [0.1, 0.2]

    mock_redis.rpush = AsyncMock(return_value=1)
    mock_redis.llen = AsyncMock(return_value=1)

    await fallback_queue.enqueue_embedding(
        operation="store_photo_embedding",
        photo_id=photo_id,
        embedding=embedding,
    )

    # Verify the queue key is used
    call_args = mock_redis.rpush.call_args
    assert call_args[0][0] == "qdrant:fallback_queue"
