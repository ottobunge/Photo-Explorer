"""Qdrant implementation of VectorStore."""

import logging
from typing import Optional
from uuid import UUID

from circuitbreaker import circuit
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.application.ports.outbound.vector_store import VectorSearchResult, VectorStore
from app.config import get_settings
from app.domain.value_objects import Embedding

logger = logging.getLogger(__name__)


# Global singleton for async client
_async_client: Optional[AsyncQdrantClient] = None


class QdrantVectorStore(VectorStore):
    """Qdrant implementation of VectorStore for photo and face embeddings."""

    # Default embedding dimensions (can be overridden)
    FACE_EMBEDDING_DIM = 512  # InsightFace embeddings

    def __init__(
        self,
        url: Optional[str] = None,
        photos_collection: Optional[str] = None,
        faces_collection: Optional[str] = None,
    ) -> None:
        global _async_client

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

    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    async def store_photo_embedding(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """
        Store a photo's CLIP embedding.

        Circuit breaker: Opens after 5 failures, recovers after 60 seconds.
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

    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    async def search_photos(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar photos by embedding.

        Circuit breaker: Opens after 5 failures, recovers after 60 seconds.
        """
        query_filter = None
        if filters:
            query_filter = self._build_filter(filters)

        response = await self._client.query_points(
            collection_name=self._photos_collection,
            query=query_embedding.to_list(),
            limit=limit,
            query_filter=query_filter,
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

    async def delete_photo_embedding(self, photo_id: UUID) -> bool:
        """Delete a photo's embedding."""
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
            logger.error(f"Error deleting photo embedding: {e}")
            return False

    async def get_photo_embedding(self, photo_id: UUID) -> Optional[Embedding]:
        """Retrieve a photo's stored embedding."""
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
            logger.error(f"Error retrieving photo embedding: {e}")
            return None

    # Face embeddings

    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    async def store_face_embedding(
        self,
        face_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """
        Store a face's embedding.

        Circuit breaker: Opens after 5 failures, recovers after 60 seconds.
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

    async def search_faces(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Search for similar faces by embedding."""
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

    async def delete_face_embedding(self, face_id: UUID) -> bool:
        """Delete a face's embedding."""
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
            logger.error(f"Error deleting face embedding: {e}")
            return False

    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    async def find_similar_faces(
        self,
        face_id: UUID,
        threshold: float = 0.6,
        limit: int = 50,
    ) -> list[VectorSearchResult]:
        """
        Find faces similar to a given face (for clustering).

        Circuit breaker: Opens after 5 failures, recovers after 60 seconds.
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
            search_results = await self._client.search(
                collection_name=self._faces_collection,
                query_vector=vector,
                limit=limit + 1,  # +1 because the query face will be included
                score_threshold=threshold,
            )

            # Filter out the query face itself
            return [
                VectorSearchResult(
                    id=UUID(result.id),
                    score=result.score,
                    payload=result.payload or {},
                )
                for result in search_results
                if result.id != str(face_id)
            ]
        except Exception as e:
            logger.error(f"Error finding similar faces: {e}")
            return []

    async def get_face_embedding(self, face_id: UUID) -> Optional[Embedding]:
        """Retrieve a face's stored embedding."""
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
            logger.error(f"Error retrieving face embedding: {e}")
            return None

    # Batch operations

    async def store_photo_embeddings_batch(
        self,
        embeddings: list[tuple[UUID, Embedding, Optional[dict]]],
    ) -> None:
        """Store multiple photo embeddings at once."""
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

    async def store_face_embeddings_batch(
        self,
        embeddings: list[tuple[UUID, Embedding, Optional[dict]]],
    ) -> None:
        """Store multiple face embeddings at once."""
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

    async def update_face_payload(self, face_id: UUID, payload: dict) -> None:
        """Update the payload (metadata) for a face embedding."""
        await self._client.set_payload(
            collection_name=self._faces_collection,
            payload=payload,
            points=[str(face_id)],
        )

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

    async def get_collection_info(self, collection_name: str) -> dict:
        """Get information about a collection."""
        info = await self._client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
        }

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
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
