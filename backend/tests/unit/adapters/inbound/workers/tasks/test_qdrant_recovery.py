"""Tests for Qdrant recovery task."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.adapters.inbound.workers.tasks.qdrant_recovery import (
    _process_face_embedding,
    _process_photo_embedding,
    _process_queue_async,
)
from app.domain.value_objects import Embedding


@pytest.fixture
def mock_embedding_task():
    """Create a mock embedding task."""
    return {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        "payload": {"filename": "test.jpg"},
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = AsyncMock()
    store.store_photo_embedding = AsyncMock()
    store.store_face_embedding = AsyncMock()
    return store


@pytest.mark.asyncio
async def test_process_photo_embedding_stores_embedding(mock_vector_store):
    """Test that _process_photo_embedding stores the embedding."""
    task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2, 0.3],
        "payload": {"filename": "photo.jpg"},
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    await _process_photo_embedding(mock_vector_store, task)

    # Verify store_photo_embedding was called
    mock_vector_store.store_photo_embedding.assert_called_once()
    call_args = mock_vector_store.store_photo_embedding.call_args

    # Verify arguments
    assert str(call_args[0][0]) == task["photo_id"]  # photo_id
    assert isinstance(call_args[0][1], Embedding)  # embedding
    assert call_args[0][1].to_list() == task["embedding"]
    assert call_args[0][2] == task["payload"]  # payload


@pytest.mark.asyncio
async def test_process_photo_embedding_without_payload(mock_vector_store):
    """Test _process_photo_embedding with missing payload."""
    task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    await _process_photo_embedding(mock_vector_store, task)

    call_args = mock_vector_store.store_photo_embedding.call_args
    assert call_args[0][2] is None  # payload should be None


@pytest.mark.asyncio
async def test_process_face_embedding_stores_embedding(mock_vector_store):
    """Test that _process_face_embedding stores the embedding."""
    face_id = uuid4()
    task = {
        "operation": "store_face_embedding",
        "photo_id": str(face_id),
        "embedding": [0.5, 0.6, 0.7, 0.8],
        "payload": {"cluster_id": "cluster123"},
        "retry_count": 1,
        "timestamp": "2024-01-01T00:01:00",
    }

    await _process_face_embedding(mock_vector_store, task)

    mock_vector_store.store_face_embedding.assert_called_once()
    call_args = mock_vector_store.store_face_embedding.call_args

    assert str(call_args[0][0]) == str(face_id)
    assert isinstance(call_args[0][1], Embedding)
    assert call_args[0][1].to_list() == task["embedding"]
    assert call_args[0][2] == task["payload"]


@pytest.mark.asyncio
async def test_process_face_embedding_without_payload(mock_vector_store):
    """Test _process_face_embedding with missing payload."""
    task = {
        "operation": "store_face_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2, 0.3],
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    await _process_face_embedding(mock_vector_store, task)

    call_args = mock_vector_store.store_face_embedding.call_args
    assert call_args[0][2] is None


@pytest.mark.asyncio
async def test_process_photo_embedding_handles_invalid_uuid():
    """Test that _process_photo_embedding raises on invalid UUID."""
    mock_vector_store = AsyncMock()
    task = {
        "operation": "store_photo_embedding",
        "photo_id": "not-a-valid-uuid",
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    with pytest.raises(ValueError):
        await _process_photo_embedding(mock_vector_store, task)


@pytest.mark.asyncio
async def test_process_face_embedding_handles_invalid_uuid():
    """Test that _process_face_embedding raises on invalid UUID."""
    mock_vector_store = AsyncMock()
    task = {
        "operation": "store_face_embedding",
        "photo_id": "invalid-uuid",
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    with pytest.raises(ValueError):
        await _process_face_embedding(mock_vector_store, task)


@pytest.mark.asyncio
async def test_process_queue_async_empty_queue():
    """Test _process_queue_async with empty queue."""
    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=0)
    mock_redis.close = AsyncMock()

    # Create an async function that returns the mock redis
    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                result = await _process_queue_async()

    assert result["processed"] == 0
    assert result["failed"] == 0
    assert result["requeued"] == 0
    mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_process_queue_async_processes_photo_embeddings():
    """Test _process_queue_async processes photo embedding tasks."""
    task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2, 0.3],
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=1)
    mock_queue.dequeue_batch = AsyncMock(side_effect=[[task], []])
    mock_vector_store.store_photo_embedding = AsyncMock()
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                result = await _process_queue_async()

    assert result["processed"] == 1
    assert result["failed"] == 0
    assert result["requeued"] == 0
    mock_vector_store.store_photo_embedding.assert_called_once()
    mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_process_queue_async_processes_face_embeddings():
    """Test _process_queue_async processes face embedding tasks."""
    task = {
        "operation": "store_face_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2, 0.3, 0.4],
        "payload": {"cluster": "1"},
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=1)
    mock_queue.dequeue_batch = AsyncMock(side_effect=[[task], []])
    mock_vector_store.store_face_embedding = AsyncMock()
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                result = await _process_queue_async()

    assert result["processed"] == 1
    assert result["failed"] == 0
    mock_vector_store.store_face_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_process_queue_async_handles_unknown_operation():
    """Test _process_queue_async with unknown operation type."""
    task = {
        "operation": "unknown_operation",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:00:00",
    }

    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=1)
    mock_queue.dequeue_batch = AsyncMock(side_effect=[[task], []])
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                result = await _process_queue_async()

    assert result["processed"] == 0
    assert result["failed"] == 1
    assert result["requeued"] == 0


@pytest.mark.asyncio
async def test_process_queue_async_retries_failed_tasks():
    """Test _process_queue_async re-queues failed tasks."""
    task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2, 0.3],
        "payload": None,
        "retry_count": 1,
        "timestamp": "2024-01-01T00:00:00",
    }

    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=1)
    mock_queue.dequeue_batch = AsyncMock(side_effect=[[task], []])
    mock_queue.requeue_with_retry = AsyncMock()
    mock_vector_store.store_photo_embedding = AsyncMock(side_effect=Exception("DB error"))
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                result = await _process_queue_async()

    assert result["processed"] == 0
    assert result["failed"] == 1
    assert result["requeued"] == 1
    mock_queue.requeue_with_retry.assert_called_once()


@pytest.mark.asyncio
async def test_process_queue_async_respects_max_retries():
    """Test _process_queue_async doesn't re-queue after max retries."""
    task = {
        "operation": "store_photo_embedding",
        "photo_id": str(uuid4()),
        "embedding": [0.1, 0.2],
        "payload": None,
        "retry_count": 3,  # Already at max retries
        "timestamp": "2024-01-01T00:00:00",
    }

    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=1)
    mock_queue.dequeue_batch = AsyncMock(side_effect=[[task], []])
    mock_queue.requeue_with_retry = AsyncMock()
    mock_vector_store.store_photo_embedding = AsyncMock(side_effect=Exception("Error"))
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                result = await _process_queue_async()

    assert result["processed"] == 0
    assert result["failed"] == 1
    assert result["requeued"] == 0  # Not re-queued
    mock_queue.requeue_with_retry.assert_not_called()


@pytest.mark.asyncio
async def test_process_queue_async_processes_multiple_batches():
    """Test _process_queue_async processes multiple batches."""
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
        "payload": None,
        "retry_count": 0,
        "timestamp": "2024-01-01T00:01:00",
    }

    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=2)
    # First batch with task1, second batch with task2
    mock_queue.dequeue_batch = AsyncMock(side_effect=[[task1], [task2], []])
    mock_vector_store.store_photo_embedding = AsyncMock()
    mock_vector_store.store_face_embedding = AsyncMock()
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                result = await _process_queue_async()

    assert result["processed"] == 2
    assert result["failed"] == 0
    assert result["requeued"] == 0
    assert mock_vector_store.store_photo_embedding.call_count == 1
    assert mock_vector_store.store_face_embedding.call_count == 1


@pytest.mark.asyncio
async def test_process_queue_async_closes_redis_connection():
    """Test _process_queue_async always closes Redis connection."""
    mock_redis = AsyncMock()
    mock_queue = AsyncMock()
    mock_vector_store = AsyncMock()

    mock_queue.queue_length = AsyncMock(return_value=0)
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with patch(
                "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantVectorStore",
                return_value=mock_vector_store,
            ):
                await _process_queue_async()

    mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_process_queue_async_closes_redis_on_error():
    """Test _process_queue_async closes Redis even when error occurs."""
    mock_redis = AsyncMock()
    mock_queue = AsyncMock()

    # Make queue_length raise an exception
    mock_queue.queue_length = AsyncMock(side_effect=Exception("Redis error"))
    mock_redis.close = AsyncMock()

    async def mock_from_url(*args, **kwargs):
        return mock_redis

    with patch(
        "app.adapters.inbound.workers.tasks.qdrant_recovery.from_url",
        side_effect=mock_from_url,
    ):
        with patch(
            "app.adapters.inbound.workers.tasks.qdrant_recovery.QdrantFallbackQueue",
            return_value=mock_queue,
        ):
            with pytest.raises(Exception):
                await _process_queue_async()

    # Redis should be closed even though exception occurred
    mock_redis.close.assert_called_once()
