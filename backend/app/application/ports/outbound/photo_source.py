"""Photo source port - Interface for fetching photos from external sources."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RemotePhotoMetadata:
    """Metadata for a photo from a remote source."""

    external_id: str
    filename: str
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    taken_at: Optional[datetime] = None
    description: Optional[str] = None

    # Camera metadata
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    focal_length: Optional[str] = None
    aperture: Optional[str] = None
    iso: Optional[int] = None
    exposure_time: Optional[str] = None

    # Source URL (may expire)
    base_url: Optional[str] = None
    product_url: Optional[str] = None


class PhotoSource(ABC):
    """Interface for fetching photos from external sources."""

    @abstractmethod
    async def list_photos(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> tuple[list[RemotePhotoMetadata], Optional[str]]:
        """
        List photos from the source.

        Args:
            page_size: Number of photos per page (max 100)
            page_token: Token for pagination

        Returns:
            Tuple of (photos, next_page_token)
        """

    @abstractmethod
    def iter_all_photos(
        self,
        page_size: int = 100,
    ) -> AsyncIterator[RemotePhotoMetadata]:
        """
        Iterate over all photos from the source.

        Args:
            page_size: Number of photos per page

        Yields:
            RemotePhotoMetadata for each photo
        """

    @abstractmethod
    async def get_photo(self, external_id: str) -> Optional[RemotePhotoMetadata]:
        """
        Get a single photo by its external ID.

        Args:
            external_id: The photo's ID in the source system

        Returns:
            RemotePhotoMetadata or None if not found
        """

    @abstractmethod
    async def get_photo_bytes(
        self,
        external_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Optional[bytes]:
        """
        Fetch the actual photo bytes.

        Used for generating embeddings during indexing.

        Args:
            external_id: The photo's ID in the source system
            width: Desired width (for resizing)
            height: Desired height (for resizing)

        Returns:
            Photo bytes or None if not found
        """

    @abstractmethod
    async def get_photo_url(
        self,
        external_id: str,
        width: int = 2048,
        height: int = 2048,
    ) -> Optional[str]:
        """
        Get a fresh URL for viewing a photo.

        URLs may expire (e.g., Google Photos baseUrl expires after 60 min).

        Args:
            external_id: The photo's ID in the source system
            width: Desired width
            height: Desired height

        Returns:
            The photo URL or None if not found
        """

    @abstractmethod
    async def get_thumbnail_url(
        self,
        external_id: str,
        width: int = 400,
        height: int = 400,
    ) -> Optional[str]:
        """
        Get a fresh URL for a photo thumbnail.

        Args:
            external_id: The photo's ID in the source system
            width: Thumbnail width
            height: Thumbnail height

        Returns:
            The thumbnail URL or None if not found
        """
