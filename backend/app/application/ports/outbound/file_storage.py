"""File storage port - Interface for file system operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional


class FileStorage(ABC):
    """Interface for file storage operations."""

    @abstractmethod
    async def save_photo(
        self,
        file: BinaryIO,
        filename: str,
    ) -> str:
        """
        Save a photo file to storage.

        Args:
            file: File-like object containing the image data
            filename: Original filename

        Returns:
            The storage path for the saved file
        """
        pass

    @abstractmethod
    async def save_thumbnail(
        self,
        image_data: bytes,
        photo_id: str,
    ) -> str:
        """
        Save a thumbnail image.

        Args:
            image_data: Thumbnail image bytes
            photo_id: The photo's unique identifier

        Returns:
            The storage path for the thumbnail
        """
        pass

    @abstractmethod
    async def save_face_crop(
        self,
        image_data: bytes,
        face_id: str,
    ) -> str:
        """
        Save a cropped face image.

        Args:
            image_data: Face crop image bytes
            face_id: The face's unique identifier

        Returns:
            The storage path for the face crop
        """
        pass

    @abstractmethod
    async def get_file(self, path: str) -> Optional[bytes]:
        """
        Read a file from storage.

        Args:
            path: The storage path

        Returns:
            File bytes or None if not found
        """
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: The storage path

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: The storage path

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    def get_absolute_path(self, storage_path: str) -> Path:
        """
        Get the absolute filesystem path for a storage path.

        Args:
            storage_path: The relative storage path

        Returns:
            Absolute Path object
        """
        pass
