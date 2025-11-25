"""Photo repository port - Interface for photo persistence."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import Photo


class PhotoRepository(ABC):
    """Interface for photo persistence operations."""

    @abstractmethod
    async def save(self, photo: Photo) -> Photo:
        """
        Persist a photo entity.

        Args:
            photo: The photo to save

        Returns:
            The saved photo (with any generated fields)
        """

    @abstractmethod
    async def find_by_id(self, photo_id: UUID) -> Optional[Photo]:
        """
        Find a photo by its ID.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            The Photo entity or None if not found
        """

    @abstractmethod
    async def find_all(
        self,
        limit: int = 20,
        offset: int = 0,
        album_id: Optional[UUID] = None,
        connector_id: Optional[UUID] = None,
    ) -> list[Photo]:
        """
        Find all photos with optional filtering.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            album_id: Optional filter by album
            connector_id: Optional filter by connector

        Returns:
            List of Photo entities
        """

    @abstractmethod
    async def delete(self, photo_id: UUID) -> bool:
        """
        Delete a photo.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def count(
        self, album_id: Optional[UUID] = None, connector_id: Optional[UUID] = None
    ) -> int:
        """
        Count photos with optional filtering.

        Args:
            album_id: Optional filter by album
            connector_id: Optional filter by connector

        Returns:
            Total count of matching photos
        """

    @abstractmethod
    async def find_by_original_path(self, path: str) -> Optional[Photo]:
        """
        Find a photo by its original filesystem path.

        Args:
            path: The original file path

        Returns:
            The Photo entity or None if not found
        """

    @abstractmethod
    async def delete_many(self, photo_ids: list[UUID]) -> int:
        """
        Delete multiple photos in a single operation.

        Args:
            photo_ids: List of photo IDs to delete

        Returns:
            Number of photos actually deleted
        """

    @abstractmethod
    async def delete_bulk_by_connector(self, connector_id: UUID) -> int:
        """
        Delete all photos associated with a connector in a single bulk operation.

        Args:
            connector_id: The connector's unique identifier

        Returns:
            Number of photos deleted
        """
