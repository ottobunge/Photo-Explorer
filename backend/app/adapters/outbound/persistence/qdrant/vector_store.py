"""Qdrant implementation of VectorStore."""

import logging
from typing import Optional
from uuid import UUID

from circuitbreaker import circuit
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.application.ports.outbound.vector_store import VectorSearchResult, VectorStore
from app.config import get_settings
from app.domain.value_objects import Embedding
from app.infrastructure.monitoring import (
    log_circuit_breaker_events,
    monitor_circuit_breaker,
)

logger = logging.getLogger(__name__)

# Qdrant-specific exceptions that should trigger circuit breaker
QDRANT_CIRCUIT_EXCEPTIONS = (
    UnexpectedResponse,
    ResponseHandlingException,
    TimeoutError,
    ConnectionError,
    OSError,  # Network-related errors
)


# Global singleton for async client
_async_client: Optional[AsyncQdrantClient] = None

# Global fallback queue instance
_fallback_queue: Optional["QdrantFallbackQueue"] = None


class QdrantVectorStore(VectorStore):
    """Qdrant implementation of VectorStore for photo and face embeddings."""

    # Default embedding dimensions (can be overridden)
    FACE_EMBEDDING_DIM = 512  # InsightFace embeddings

    def __init__(
        self,
        url: Optional[str] = None,
        photos_collection: Optional[str] = None,
        faces_collection: Optional[str] = None,
        fallback_queue: Optional["QdrantFallbackQueue"] = None,
    ) -> None:
        global _async_client
        global _fallback_queue

        settings = get_settings()
        self._url = url or settings.qdrant_url
        self._photos_collection = photos_collection or settings.qdrant_collection_photos
        self._faces_collection = faces_collection or settings.qdrant_collection_faces

        # Get CLIP embedding dimension from config
        from app.infrastructure.models.config import get_model_config

        model_config = get_model_config()
        self._clip_embedding_dim = model_config.clip.embedding_dim

        # Use sync client for initialization only
        self._sync_client = QdrantClient(url=self._url)
        self._ensure_collections()

        # Create async client singleton
        if _async_client is None:
            _async_client = AsyncQdrantClient(url=self._url)
        self._client = _async_client

        # Store fallback queue for circuit breaker integration
        if fallback_queue is not None:
            _fallback_queue = fallback_queue
        self._fallback_queue = _fallback_queue

    def _ensure_collections(self) -> None:
        """Ensure required collections exist."""
        self._ensure_collection(
            self._photos_collection,
            self._clip_embedding_dim,
        )
        self._ensure_collection(
            self._faces_collection,
            self.FACE_EMBEDDING_DIM,
        )

    def _ensure_collection(self, name: str, vector_size: int) -> None:
        """Create a collection if it doesn't exist (uses sync client for init)."""
        try:
            self._sync_client.get_collection(name)
            logger.debug(f"Collection {name} already exists")
        except (UnexpectedResponse, Exception):
            logger.info(f"Creating collection {name} with vector size {vector_size}")
            self._sync_client.create_collection(
                collection_name=name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    # Photo embeddings

    async def _store_photo_embedding_impl(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """Internal implementation of photo embedding storage (with circuit breaker).

        This method is wrapped with the @circuit decorator to handle failures.
        When the circuit is open, exceptions are caught and the operation is queued.
        """
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
        """Photo embedding storage with circuit breaker protection."""
        await self._store_photo_embedding_impl(photo_id, embedding, payload)

    async def store_photo_embedding(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """Store a photo's CLIP embedding with fallback queue support.

        Args:
            photo_id: UUID of the photo
            embedding: CLIP embedding vector
            payload: Optional metadata to store with the embedding

        Returns:
            None

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker & fallback:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - When open: operation queued to Redis for async retry
            - Fallback task processes queue when Qdrant recovers

        Note:
            Photo upload always succeeds (operation either stored immediately
            or queued for later processing). Returns immediately without waiting
            for storage confirmation.
        """
        try:
            await self._store_photo_embedding_circuit_breaker(photo_id, embedding, payload)
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

    @log_circuit_breaker_events
    @monitor_circuit_breaker("search_photos")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def search_photos(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[dict] = None,
        score_threshold: Optional[float] = None,
    ) -> list[VectorSearchResult]:
        """Search for similar photos by embedding.

        Args:
            query_embedding: The embedding vector to search for
            limit: Maximum number of results to return (default 20)
            filters: Optional filters to apply (Qdrant format)
            score_threshold: Optional minimum similarity score (0.0-1.0).
                           Only return results with score >= threshold.

        Returns:
            List of VectorSearchResult objects sorted by relevance score (highest first).
            Returns empty list when circuit is open (Qdrant unavailable).

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: Returns empty list [] when circuit is open

        Note:
            Fallback behavior returns empty results gracefully when Qdrant is unavailable.
            Frontend should indicate "Search temporarily unavailable" to users.
        """
        query_filter = None
        if filters:
            query_filter = self._build_filter(filters)

        response = await self._client.query_points(
            collection_name=self._photos_collection,
            query=query_embedding.to_list(),
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )
        results = response.points

        return [
            VectorSearchResult(
                id=UUID(result.id),
                score=result.score,
                payload=result.payload or {},
            )
            for result in results
        ]

    @log_circuit_breaker_events
    @monitor_circuit_breaker("delete_photo_embedding")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def delete_photo_embedding(self, photo_id: UUID) -> bool:
        """Delete a photo's embedding from the vector store.

        Args:
            photo_id: UUID of the photo whose embedding should be deleted

        Returns:
            True if deletion succeeded, False if photo not found or error occurred.

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: Returns False when circuit is open

        Note:
            Failed deletions (when circuit is open) are logged but don't fail the operation.
            Photos are still deleted from the database, just not from the vector store.
            Once Qdrant recovers, the embedding should be deleted manually or via cleanup task.
        """
        try:
            await self._client.delete(
                collection_name=self._photos_collection,
                points_selector=qdrant_models.PointIdsList(
                    points=[str(photo_id)],
                ),
            )
            logger.debug(f"Deleted embedding for photo {photo_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting photo embedding {photo_id}: {e}")
            return False

    @log_circuit_breaker_events
    @monitor_circuit_breaker("get_photo_embedding")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def get_photo_embedding(self, photo_id: UUID) -> Optional[Embedding]:
        """Retrieve a photo's stored embedding vector.

        Args:
            photo_id: UUID of the photo whose embedding to retrieve

        Returns:
            Embedding object if found, None if not found or on error.

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: Returns None when circuit is open

        Note:
            Returns None for both "not found" and "Qdrant unavailable" cases.
            When circuit is open, callers cannot distinguish between missing embedding
            and temporary unavailability. Consider adding metrics to track this.
        """
        try:
            results = await self._client.retrieve(
                collection_name=self._photos_collection,
                ids=[str(photo_id)],
                with_vectors=True,
            )
            if results:
                vector = results[0].vector
                if isinstance(vector, list):
                    return Embedding(vector=vector)
            return None
        except Exception as e:
            logger.error(f"Error retrieving photo embedding {photo_id}: {e}")
            return None

    # Face embeddings

    async def _store_face_embedding_impl(
        self,
        face_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """Internal implementation of face embedding storage (with circuit breaker).

        This method is wrapped with the @circuit decorator to handle failures.
        When the circuit is open, exceptions are caught and the operation is queued.
        """
        point = qdrant_models.PointStruct(
            id=str(face_id),
            vector=embedding.to_list(),
            payload=payload or {},
        )
        await self._client.upsert(
            collection_name=self._faces_collection,
            points=[point],
        )
        logger.debug(f"Stored embedding for face {face_id}")

    @log_circuit_breaker_events
    @monitor_circuit_breaker("store_face_embedding")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def _store_face_embedding_circuit_breaker(
        self,
        face_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """Face embedding storage with circuit breaker protection."""
        await self._store_face_embedding_impl(face_id, embedding, payload)

    async def store_face_embedding(
        self,
        face_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """Store a face's embedding for clustering and recognition with fallback queue support.

        Args:
            face_id: UUID of the detected face
            embedding: InsightFace embedding vector (512 dimensions)
            payload: Optional metadata (cluster_id, person_id, detection_box, etc.)

        Returns:
            None

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker & fallback:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - When open: operation queued to Redis for async retry
            - Fallback task processes queue when Qdrant recovers

        Note:
            Face detection always succeeds (operation either stored immediately
            or queued for later processing). Faces will be available for clustering
            once circuit recovers and embeddings are stored.
        """
        try:
            await self._store_face_embedding_circuit_breaker(face_id, embedding, payload)
        except Exception as e:
            # Circuit breaker is open - queue the operation
            if self._fallback_queue is not None:
                logger.info(
                    f"Qdrant unavailable - queuing face embedding",
                    extra={
                        "face_id": str(face_id),
                        "error": str(e)[:100],
                        "error_type": type(e).__name__,
                    },
                )
                await self._fallback_queue.enqueue_embedding(
                    operation="store_face_embedding",
                    photo_id=face_id,
                    embedding=embedding.to_list(),
                    payload=payload,
                )
            else:
                # No fallback queue configured - log warning
                logger.warning(
                    f"Qdrant unavailable and no fallback queue configured",
                    extra={
                        "face_id": str(face_id),
                        "error": str(e)[:100],
                    },
                )

    @log_circuit_breaker_events
    @monitor_circuit_breaker("search_faces")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def search_faces(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Search for similar faces by embedding vector.

        Args:
            query_embedding: Face embedding vector to search for
            limit: Maximum number of similar faces to return (default 20)
            filters: Optional filters (e.g., by cluster_id or person_id)

        Returns:
            List of VectorSearchResult objects representing similar faces,
            sorted by similarity score (highest first).
            Returns empty list when circuit is open (Qdrant unavailable).

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: Returns empty list [] when circuit is open

        Note:
            Used for face clustering to find similar faces. When Qdrant is down,
            clustering cannot proceed, but existing clusters remain intact.
        """
        query_filter = None
        if filters:
            query_filter = self._build_filter(filters)

        results = await self._client.search(
            collection_name=self._faces_collection,
            query_vector=query_embedding.to_list(),
            limit=limit,
            query_filter=query_filter,
        )

        return [
            VectorSearchResult(
                id=UUID(result.id),
                score=result.score,
                payload=result.payload or {},
            )
            for result in results
        ]

    @log_circuit_breaker_events
    @monitor_circuit_breaker("delete_face_embedding")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def delete_face_embedding(self, face_id: UUID) -> bool:
        """Delete a face's embedding from the vector store.

        Args:
            face_id: UUID of the face whose embedding should be deleted

        Returns:
            True if deletion succeeded, False if face not found or error occurred.

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: Returns False when circuit is open

        Note:
            Failed deletions (when circuit is open) are logged but don't fail the operation.
            Faces are still deleted from the database, just not from the vector store.
            Once Qdrant recovers, the embedding should be deleted via cleanup task.
        """
        try:
            await self._client.delete(
                collection_name=self._faces_collection,
                points_selector=qdrant_models.PointIdsList(
                    points=[str(face_id)],
                ),
            )
            logger.debug(f"Deleted embedding for face {face_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting face embedding {face_id}: {e}")
            return False

    @log_circuit_breaker_events
    @monitor_circuit_breaker("find_similar_faces")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def find_similar_faces(
        self,
        face_id: UUID,
        threshold: float = 0.6,
        limit: int = 50,
    ) -> list[VectorSearchResult]:
        """Find faces similar to a given face for clustering.

        Args:
            face_id: UUID of the reference face
            threshold: Minimum similarity score (0.0-1.0, default 0.6)
            limit: Maximum number of similar faces to return (default 50)

        Returns:
            List of VectorSearchResult objects for similar faces (excluding query face),
            sorted by similarity score (highest first).
            Returns empty list if face not found or on error.

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: Returns empty list [] when circuit is open

        Note:
            This is a critical operation for face clustering. When Qdrant is down,
            new faces cannot be clustered, but existing clusters remain intact.
            The query face itself is excluded from results even if it matches the threshold.
        """
        # First, get the face's embedding
        try:
            results = await self._client.retrieve(
                collection_name=self._faces_collection,
                ids=[str(face_id)],
                with_vectors=True,
            )
            if not results:
                return []

            vector = results[0].vector
            if not isinstance(vector, list):
                return []

            # Search for similar faces
            search_response = await self._client.query_points(
                collection_name=self._faces_collection,
                query=vector,
                limit=limit + 1,  # +1 because the query face will be included
                score_threshold=threshold,
            )

            # Filter out the query face itself
            return [
                VectorSearchResult(
                    id=UUID(str(result.id)),
                    score=result.score,
                    payload=result.payload or {},
                )
                for result in search_response.points
                if str(result.id) != str(face_id)
            ]
        except Exception as e:
            logger.error(f"Error finding similar faces for {face_id}: {e}")
            return []

    @log_circuit_breaker_events
    @monitor_circuit_breaker("get_face_embedding")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def get_face_embedding(self, face_id: UUID) -> Optional[Embedding]:
        """Retrieve a face's stored embedding vector.

        Args:
            face_id: UUID of the face whose embedding to retrieve

        Returns:
            Embedding object if found, None if not found or on error.

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: Returns None when circuit is open

        Note:
            Returns None for both "not found" and "Qdrant unavailable" cases.
            When circuit is open, callers cannot distinguish between missing embedding
            and temporary unavailability. Consider adding metrics to track this.
        """
        try:
            results = await self._client.retrieve(
                collection_name=self._faces_collection,
                ids=[str(face_id)],
                with_vectors=True,
            )
            if results:
                vector = results[0].vector
                if isinstance(vector, list):
                    return Embedding(vector=vector)
            return None
        except Exception as e:
            logger.error(f"Error retrieving face embedding {face_id}: {e}")
            return None

    # Batch operations

    @log_circuit_breaker_events
    @monitor_circuit_breaker("store_photo_embeddings_batch")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def store_photo_embeddings_batch(
        self,
        embeddings: list[tuple[UUID, Embedding, Optional[dict]]],
    ) -> None:
        """Store multiple photo embeddings in a single batch operation.

        Args:
            embeddings: List of (photo_id, embedding, payload) tuples

        Returns:
            None

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: None (callers should handle loss of search capability)

        Note:
            Batch operations are more efficient than individual stores.
            Empty input list is idempotent (no operation performed).
            When circuit is open, photo embeddings are not stored, but photo data
            remains safe in the database.
        """
        if not embeddings:
            return

        points = [
            qdrant_models.PointStruct(
                id=str(photo_id),
                vector=embedding.to_list(),
                payload=payload or {},
            )
            for photo_id, embedding, payload in embeddings
        ]
        await self._client.upsert(
            collection_name=self._photos_collection,
            points=points,
        )
        logger.debug(f"Stored {len(embeddings)} photo embeddings in batch")

    @log_circuit_breaker_events
    @monitor_circuit_breaker("store_face_embeddings_batch")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def store_face_embeddings_batch(
        self,
        embeddings: list[tuple[UUID, Embedding, Optional[dict]]],
    ) -> None:
        """Store multiple face embeddings in a single batch operation.

        Args:
            embeddings: List of (face_id, embedding, payload) tuples

        Returns:
            None

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: None (callers should handle loss of clustering capability)

        Note:
            Batch operations are more efficient than individual stores.
            Empty input list is idempotent (no operation performed).
            When circuit is open, face embeddings are not stored, but detected faces
            remain safe in the database.
        """
        if not embeddings:
            return

        points = [
            qdrant_models.PointStruct(
                id=str(face_id),
                vector=embedding.to_list(),
                payload=payload or {},
            )
            for face_id, embedding, payload in embeddings
        ]
        await self._client.upsert(
            collection_name=self._faces_collection,
            points=points,
        )
        logger.debug(f"Stored {len(embeddings)} face embeddings in batch")

    @log_circuit_breaker_events
    @monitor_circuit_breaker("update_face_payload")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def update_face_payload(self, face_id: UUID, payload: dict) -> None:
        """Update the payload (metadata) for a face embedding.

        Args:
            face_id: UUID of the face whose payload should be updated
            payload: Dictionary of metadata to update (cluster_id, person_id, etc.)

        Returns:
            None

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: None (callers should handle update failures gracefully)

        Note:
            Used for updating face cluster assignments and metadata.
            When circuit is open, updates cannot be persisted to vector store.
            Updates to database metadata still succeed; only vector store sync is delayed.
        """
        await self._client.set_payload(
            collection_name=self._faces_collection,
            payload=payload,
            points=[str(face_id)],
        )

    @log_circuit_breaker_events
    @monitor_circuit_breaker("update_face_payloads_batch")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def update_face_payloads_batch(
        self,
        updates: list[tuple[UUID, dict]],
    ) -> None:
        """Update payloads for multiple faces in a single batch operation.

        Uses Qdrant's set_payload with multiple point IDs for efficiency.

        Args:
            updates: List of (face_id, payload_updates) tuples.
                    Payloads are grouped to minimize Qdrant calls.

        Returns:
            None

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - Fallback: None (callers should handle update failures gracefully)

        Note:
            Batch operation groups updates by payload to minimize Qdrant calls.
            Empty input list is idempotent (no operation performed).
            Used for updating cluster assignments across multiple detected faces.
            When circuit is open, updates cannot be persisted to vector store.
        """
        if not updates:
            return

        # Group updates by payload to reduce Qdrant calls
        # All updates have the same payload structure, just different values
        # So we can do one set_payload call per unique payload update
        payload_map: dict[str, tuple[dict, list[str]]] = {}

        for face_id, payload in updates:
            # Convert payload to hashable key for grouping
            payload_key = str(sorted(payload.items()))
            if payload_key not in payload_map:
                payload_map[payload_key] = (payload, [])
            payload_map[payload_key][1].append(str(face_id))

        # Execute batch updates
        for payload, point_ids in payload_map.values():
            await self._client.set_payload(
                collection_name=self._faces_collection,
                payload=payload,
                points=point_ids,
            )

        logger.debug(f"Batch updated payloads for {len(updates)} faces")

    def _build_filter(self, filters: dict) -> qdrant_models.Filter:
        """Build a Qdrant filter from a dictionary."""
        conditions = []

        for key, value in filters.items():
            if isinstance(value, list):
                # Multiple values = OR condition
                conditions.append(
                    qdrant_models.FieldCondition(
                        key=key,
                        match=qdrant_models.MatchAny(any=value),
                    )
                )
            elif isinstance(value, dict):
                # Range filter
                if "gte" in value or "lte" in value:
                    conditions.append(
                        qdrant_models.FieldCondition(
                            key=key,
                            range=qdrant_models.Range(
                                gte=value.get("gte"),
                                lte=value.get("lte"),
                            ),
                        )
                    )
            else:
                # Exact match
                conditions.append(
                    qdrant_models.FieldCondition(
                        key=key,
                        match=qdrant_models.MatchValue(value=value),
                    )
                )

        return qdrant_models.Filter(must=conditions)

    @log_circuit_breaker_events
    @monitor_circuit_breaker("get_collection_info")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def get_collection_info(self, collection_name: str) -> dict:
        """Get information about a Qdrant collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection metadata (vectors_count, points_count, status)

        Raises:
            UnexpectedResponse: If Qdrant returns an unexpected response
            ResponseHandlingException: If response handling fails
            TimeoutError: If Qdrant request times out
            ConnectionError: If Qdrant connection fails
            OSError: If network error occurs

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
        """
        info = await self._client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
        }

    @log_circuit_breaker_events
    @monitor_circuit_breaker("health_check")
    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=QDRANT_CIRCUIT_EXCEPTIONS,
    )
    async def health_check(self) -> bool:
        """Check if Qdrant service is healthy and accessible.

        Returns:
            True if Qdrant is healthy and accessible, False otherwise.
            Returns False when circuit is open (indicating repeated failures).

        Raises:
            No exceptions are raised; failures are caught and False is returned.

        Circuit breaker:
            - Opens after 5 consecutive Qdrant connectivity failures
            - Stays open for 60 seconds before recovery attempt
            - When open, this method returns False immediately without calling Qdrant

        Note:
            This is a monitoring/diagnostic method. When circuit is open,
            the boolean return value False reliably indicates Qdrant is unavailable.
        """
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    async def cleanup(self) -> None:
        """
        Cleanup Qdrant client connections.

        This is useful for graceful shutdown to properly close connections.
        Note: The async client will be recreated on next use due to singleton pattern.
        """
        global _async_client
        if _async_client is not None:
            try:
                await _async_client.close()
                logger.info("Closed Qdrant async client")
            except Exception as e:
                logger.warning(f"Error closing Qdrant async client: {e}")
            finally:
                _async_client = None

        # Close sync client if it exists
        if hasattr(self, "_sync_client") and self._sync_client is not None:
            try:
                self._sync_client.close()
                logger.info("Closed Qdrant sync client")
            except Exception as e:
                logger.warning(f"Error closing Qdrant sync client: {e}")


async def cleanup_vector_store() -> None:
    """
    Cleanup the global Qdrant client singleton.

    This should be called during worker shutdown for graceful cleanup.
    """
    global _async_client
    if _async_client is not None:
        try:
            await _async_client.close()
            logger.info("Cleaned up global Qdrant async client")
        except Exception as e:
            logger.warning(f"Error cleaning up Qdrant async client: {e}")
        finally:
            _async_client = None


async def ensure_collections() -> None:
    """
    Ensure that required Qdrant collections exist at application startup.

    This function should be called during application lifespan startup.
    It will create the photo_embeddings and face_embeddings collections
    if they don't exist, with proper vector configurations.

    Raises:
        Exception: If Qdrant is unreachable or collection creation fails
    """
    settings = get_settings()

    # Get model config for embedding dimensions
    from app.infrastructure.models.config import get_model_config

    model_config = get_model_config()

    # Use sync client for initialization
    try:
        sync_client = QdrantClient(url=settings.qdrant_url)

        # Ensure photo embeddings collection
        try:
            sync_client.get_collection(settings.qdrant_collection_photos)
            logger.info(f"Collection {settings.qdrant_collection_photos} already exists")
        except (UnexpectedResponse, Exception):
            logger.info(
                f"Creating collection {settings.qdrant_collection_photos} "
                f"with vector size {model_config.clip.embedding_dim}"
            )
            sync_client.create_collection(
                collection_name=settings.qdrant_collection_photos,
                vectors_config=qdrant_models.VectorParams(
                    size=model_config.clip.embedding_dim,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(f"Successfully created collection {settings.qdrant_collection_photos}")

        # Ensure face embeddings collection
        try:
            sync_client.get_collection(settings.qdrant_collection_faces)
            logger.info(f"Collection {settings.qdrant_collection_faces} already exists")
        except (UnexpectedResponse, Exception):
            logger.info(
                f"Creating collection {settings.qdrant_collection_faces} "
                f"with vector size {QdrantVectorStore.FACE_EMBEDDING_DIM}"
            )
            sync_client.create_collection(
                collection_name=settings.qdrant_collection_faces,
                vectors_config=qdrant_models.VectorParams(
                    size=QdrantVectorStore.FACE_EMBEDDING_DIM,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(f"Successfully created collection {settings.qdrant_collection_faces}")

        # Close sync client
        sync_client.close()
        logger.info("Qdrant collections verified and ready")

    except Exception as e:
        logger.critical(f"Failed to connect to Qdrant or create collections: {e}", exc_info=True)
        raise
