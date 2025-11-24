"""Album repository port - Interface for album persistence."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import Album


class AlbumRepository(ABC):
    """Interface for album persistence operations."""

    @abstractmethod
    async def save(self, album: Album) -> Album:
        """
        Persist an album entity.

        Args:
            album: The album to save

        Returns:
            The saved album
        """
        pass

    @abstractmethod
    async def find_by_id(self, album_id: UUID) -> Optional[Album]:
        """
        Find an album by its ID.

        Args:
            album_id: The album's unique identifier

        Returns:
            The Album entity or None if not found
        """
        pass

    @abstractmethod
    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Album]:
        """
        Find all albums with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Album entities
        """
        pass

    @abstractmethod
    async def delete(self, album_id: UUID) -> bool:
        """
        Delete an album.

        Args:
            album_id: The album's unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """
        Count all albums.

        Returns:
            Total count of albums
        """
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Album]:
        """
        Find an album by its name.

        Args:
            name: The album name

        Returns:
            The Album entity or None if not found
        """
        pass
