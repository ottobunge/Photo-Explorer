"""Vector store port - Interface for vector similarity operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from app.domain.value_objects import Embedding

# Payload can contain various metadata fields (photo_id, cluster_id, face_id, etc)
# We use Any for flexibility across different search result contexts.
PayloadDict = dict[str, Any]  # type: ignore[explicit-any]


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""

    id: UUID
    score: float
    payload: PayloadDict


class VectorStore(ABC):
    """Interface for vector storage and similarity search operations."""

    # Photo embeddings

    @abstractmethod
    async def store_photo_embedding(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: Optional[PayloadDict] = None,
    ) -> None:
        """
        Store a photo's CLIP embedding.

        Args:
            photo_id: The photo's unique identifier
            embedding: The CLIP embedding vector
            payload: Optional metadata to store with the embedding
        """

    @abstractmethod
    async def search_photos(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[PayloadDict] = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar photos by embedding.

        Args:
            query_embedding: The query embedding vector
            limit: Maximum number of results
            filters: Optional Qdrant filters

        Returns:
            List of search results with scores
        """

    @abstractmethod
    async def delete_photo_embedding(self, photo_id: UUID) -> bool:
        """
        Delete a photo's embedding.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def get_photo_embedding(self, photo_id: UUID) -> Optional[Embedding]:
        """
        Retrieve a photo's stored embedding.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            The embedding or None if not found
        """

    # Face embeddings

    @abstractmethod
    async def store_face_embedding(
        self,
        face_id: UUID,
        embedding: Embedding,
        payload: Optional[PayloadDict] = None,
    ) -> None:
        """
        Store a face's embedding.

        Args:
            face_id: The face's unique identifier
            embedding: The face embedding vector
            payload: Optional metadata (photo_id, cluster_id)
        """

    @abstractmethod
    async def search_faces(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[PayloadDict] = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar faces by embedding.

        Args:
            query_embedding: The query embedding vector
            limit: Maximum number of results
            filters: Optional Qdrant filters

        Returns:
            List of search results with scores
        """

    @abstractmethod
    async def delete_face_embedding(self, face_id: UUID) -> bool:
        """
        Delete a face's embedding.

        Args:
            face_id: The face's unique identifier

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def find_similar_faces(
        self,
        face_id: UUID,
        threshold: float = 0.6,
        limit: int = 50,
    ) -> list[VectorSearchResult]:
        """
        Find faces similar to a given face (for clustering).

        Args:
            face_id: The face's unique identifier
            threshold: Minimum similarity threshold
            limit: Maximum number of results

        Returns:
            List of similar faces with scores
        """

    @abstractmethod
    async def update_face_payload(
        self, face_id: UUID, payload: PayloadDict
    ) -> None:
        """Update face embedding metadata in vector store.

        Args:
            face_id: UUID of the face
            payload: Metadata to update (e.g., {"cluster_id": "..."})
        """

    # TODO(performance): Batch face clustering operations
    # Currently face clustering processes 1,000+ faces one-by-one with individual
    # vector searches and payload updates. This is very slow.
    #
    # To optimize, add these batch methods:
    #
    # @abstractmethod
    # async def get_face_embeddings_batch(
    #     self,
    #     face_ids: list[UUID]
    # ) -> dict[UUID, Embedding]:
    #     """
    #     Retrieve multiple face embeddings in a single query.
    #
    #     Args:
    #         face_ids: List of face IDs to retrieve
    #
    #     Returns:
    #         Dictionary mapping face IDs to their embeddings
    #     """
    #
    # @abstractmethod
    # async def update_face_payloads_batch(
    #     self,
    #     updates: list[tuple[UUID, dict]]
    # ) -> None:
    #     """
    #     Update payloads for multiple faces in a single batch operation.
    #
    #     Args:
    #         updates: List of (face_id, payload_updates) tuples
    #     """
    #
    # With these methods, clustering could:
    # 1. Load unclustered faces in batches of 100
    # 2. Get all embeddings at once (1 call instead of 100)
    # 3. Cluster in-memory using cosine similarity
    # 4. Batch update vector store payloads (1 call instead of 100)
    #
    # Expected performance improvement: 10-100x for large datasets
