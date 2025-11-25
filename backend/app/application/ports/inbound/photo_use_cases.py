"""Photo use cases - Inbound port for photo operations."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from uuid import UUID

from app.domain.entities import Photo


class PhotoUseCases(ABC):
    """Interface defining photo-related use cases."""

    @abstractmethod
    async def upload_photo(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        album_id: Optional[UUID] = None,
    ) -> Photo:
        """
        Upload a new photo.

        Args:
            file: File-like object containing the image data
            filename: Original filename
            content_type: MIME type of the file
            album_id: Optional album to add the photo to

        Returns:
            The created Photo entity with processing status "pending"
        """

    @abstractmethod
    async def get_photo(self, photo_id: UUID) -> Optional[Photo]:
        """
        Get a photo by ID.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            The Photo entity or None if not found
        """

    @abstractmethod
    async def list_photos(
        self,
        limit: int = 20,
        offset: int = 0,
        album_id: Optional[UUID] = None,
    ) -> list[Photo]:
        """
        List photos with pagination.

        Args:
            limit: Maximum number of photos to return
            offset: Number of photos to skip
            album_id: Optional filter by album

        Returns:
            List of Photo entities
        """

    @abstractmethod
    async def delete_photo(self, photo_id: UUID) -> bool:
        """
        Delete a photo and all associated data.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def get_photo_file(self, photo_id: UUID) -> Optional[tuple[bytes, str]]:
        """
        Get the original photo file.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            Tuple of (file_bytes, content_type) or None if not found
        """

    @abstractmethod
    async def get_photo_thumbnail(self, photo_id: UUID) -> Optional[tuple[bytes, str]]:
        """
        Get the photo thumbnail.

        Args:
            photo_id: The photo's unique identifier

        Returns:
            Tuple of (file_bytes, content_type) or None if not found
        """
