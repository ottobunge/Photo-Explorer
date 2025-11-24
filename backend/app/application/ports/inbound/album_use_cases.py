"""Album use cases - Inbound port for album operations."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import Album


class AlbumUseCases(ABC):
    """Interface defining album-related use cases."""

    @abstractmethod
    async def create_album(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Album:
        """
        Create a new album.

        Args:
            name: Album name
            description: Optional description

        Returns:
            The created Album entity
        """
        pass

    @abstractmethod
    async def get_album(self, album_id: UUID) -> Optional[Album]:
        """
        Get an album by ID.

        Args:
            album_id: The album's unique identifier

        Returns:
            The Album entity or None if not found
        """
        pass

    @abstractmethod
    async def list_albums(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Album]:
        """
        List all albums with pagination.

        Args:
            limit: Maximum number of albums to return
            offset: Number of albums to skip

        Returns:
            List of Album entities
        """
        pass

    @abstractmethod
    async def update_album(
        self,
        album_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Album]:
        """
        Update an album.

        Args:
            album_id: The album's unique identifier
            name: New name (optional)
            description: New description (optional)

        Returns:
            The updated Album entity or None if not found
        """
        pass

    @abstractmethod
    async def delete_album(self, album_id: UUID) -> bool:
        """
        Delete an album.

        Args:
            album_id: The album's unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def add_photos_to_album(
        self,
        album_id: UUID,
        photo_ids: list[UUID],
    ) -> Album:
        """
        Add photos to an album.

        Args:
            album_id: The album's unique identifier
            photo_ids: List of photo IDs to add

        Returns:
            The updated Album entity
        """
        pass

    @abstractmethod
    async def remove_photos_from_album(
        self,
        album_id: UUID,
        photo_ids: list[UUID],
    ) -> Album:
        """
        Remove photos from an album.

        Args:
            album_id: The album's unique identifier
            photo_ids: List of photo IDs to remove

        Returns:
            The updated Album entity
        """
        pass

    @abstractmethod
    async def set_album_cover(
        self,
        album_id: UUID,
        photo_id: UUID,
    ) -> Album:
        """
        Set the cover photo for an album.

        Args:
            album_id: The album's unique identifier
            photo_id: The photo ID to use as cover

        Returns:
            The updated Album entity
        """
        pass
