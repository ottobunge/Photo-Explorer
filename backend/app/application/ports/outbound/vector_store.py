"""Vector store port - Interface for vector similarity operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.value_objects import Embedding


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""

    id: UUID
    score: float
    payload: dict


class VectorStore(ABC):
    """Interface for vector storage and similarity search operations."""

    # Photo embeddings

    @abstractmethod
    async def store_photo_embedding(
        self,
        photo_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """
        Store a photo's CLIP embedding.

        Args:
            photo_id: The photo's unique identifier
            embedding: The CLIP embedding vector
            payload: Optional metadata to store with the embedding
        """
        pass

    @abstractmethod
    async def search_photos(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[dict] = None,
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
        pass

    @abstractmethod
    async def delete_photo_embedding(self, photo_id: UUID) -> bool:
        """
        Delete a photo's embedding.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_photo_embedding(self, photo_id: UUID) -> Optional[Embedding]:
        """
        Retrieve a photo's stored embedding.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            The embedding or None if not found
        """
        pass

    # Face embeddings

    @abstractmethod
    async def store_face_embedding(
        self,
        face_id: UUID,
        embedding: Embedding,
        payload: Optional[dict] = None,
    ) -> None:
        """
        Store a face's embedding.

        Args:
            face_id: The face's unique identifier
            embedding: The face embedding vector
            payload: Optional metadata (photo_id, cluster_id)
        """
        pass

    @abstractmethod
    async def search_faces(
        self,
        query_embedding: Embedding,
        limit: int = 20,
        filters: Optional[dict] = None,
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
        pass

    @abstractmethod
    async def delete_face_embedding(self, face_id: UUID) -> bool:
        """
        Delete a face's embedding.

        Args:
            face_id: The face's unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

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
        pass
