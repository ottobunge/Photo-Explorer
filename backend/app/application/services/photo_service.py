"""Photo service implementing PhotoUseCases."""

import logging
from typing import BinaryIO, Optional
from uuid import UUID

from app.application.ports.inbound import PhotoUseCases
from app.application.ports.outbound import (
    FileStorage,
    PhotoRepository,
    VectorStore,
)
from app.domain.entities import Photo

logger = logging.getLogger(__name__)


class PhotoService(PhotoUseCases):
    """
    Implementation of photo use cases.

    Handles photo upload, retrieval, and deletion operations.
    """

    def __init__(
        self,
        photo_repo: PhotoRepository,
        file_storage: FileStorage,
        vector_store: VectorStore,
    ) -> None:
        self._photo_repo = photo_repo
        self._file_storage = file_storage
        self._vector_store = vector_store

    async def upload_photo(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        album_id: Optional[UUID] = None,
        connector_type: str = "local",
        connector_id: Optional[UUID] = None,
    ) -> Photo:
        """Upload a new photo.

        Args:
            file: Binary file data
            filename: Original filename
            content_type: MIME type
            album_id: Optional album to add photo to
            connector_type: Type of connector ("local", "upload", etc.)
            connector_id: ID of connector to associate with

        Returns:
            Created Photo entity
        """
        # Save file to storage
        storage_path = await self._file_storage.save_photo(file, filename)

        # Create photo entity
        photo = Photo.create(
            filename=filename,
            storage_path=storage_path,
            album_id=album_id,
            connector_type=connector_type,
            connector_id=connector_id,
        )
        photo.mime_type = content_type

        # Save to database
        photo = await self._photo_repo.save(photo)

        logger.info(
            f"Uploaded photo {photo.id.value}: {filename}",
            extra={
                "connector_type": connector_type,
                "connector_id": str(connector_id) if connector_id else None,
            },
        )
        return photo

    async def get_photo(self, photo_id: UUID) -> Optional[Photo]:
        """Get a photo by ID."""
        return await self._photo_repo.find_by_id(photo_id)

    async def list_photos(
        self,
        limit: int = 20,
        offset: int = 0,
        album_id: Optional[UUID] = None,
    ) -> list[Photo]:
        """List photos with pagination."""
        return await self._photo_repo.find_all(
            limit=limit,
            offset=offset,
            album_id=album_id,
        )

    async def delete_photo(self, photo_id: UUID) -> bool:
        """Delete a photo and all associated data."""
        photo = await self._photo_repo.find_by_id(photo_id)
        if not photo:
            return False

        # Delete embedding from vector store
        await self._vector_store.delete_photo_embedding(photo_id)

        # Delete files from storage
        if photo.storage_path:
            await self._file_storage.delete_file(photo.storage_path)
        if photo.thumbnail_path:
            await self._file_storage.delete_file(photo.thumbnail_path)

        # Delete from database (cascades to faces)
        deleted = await self._photo_repo.delete(photo_id)

        if deleted:
            logger.info(f"Deleted photo {photo_id}")

        return deleted

    async def get_photo_file(self, photo_id: UUID) -> Optional[tuple[bytes, str]]:
        """Get the original photo file."""
        photo = await self._photo_repo.find_by_id(photo_id)
        if not photo:
            return None

        # For local photos with storage_path
        if photo.storage_path:
            file_bytes = await self._file_storage.get_file(photo.storage_path)
            if file_bytes:
                content_type = photo.mime_type or "image/jpeg"
                return (file_bytes, content_type)

        # For local connector photos, read from source
        if photo.connector_type == "local" and photo.source_path:
            file_bytes = await self._file_storage.read_source_file(photo.source_path)
            if file_bytes:
                content_type = photo.mime_type or "image/jpeg"
                return (file_bytes, content_type)

        # For remote photos, would need to fetch from source
        # (handled by connector)
        return None

    async def get_photo_thumbnail(self, photo_id: UUID) -> Optional[tuple[bytes, str]]:
        """Get the photo thumbnail."""
        photo = await self._photo_repo.find_by_id(photo_id)
        if not photo:
            return None

        # Try cached thumbnail first
        if photo.thumbnail_path:
            file_bytes = await self._file_storage.get_file(photo.thumbnail_path)
            if file_bytes:
                return (file_bytes, "image/jpeg")

        # For remote photos with cached thumbnail
        if photo.cached_thumbnail_path and photo.cached_thumbnail_valid:
            file_bytes = await self._file_storage.get_file(photo.cached_thumbnail_path)
            if file_bytes:
                return (file_bytes, "image/jpeg")

        return None

    async def count_photos(self, album_id: Optional[UUID] = None) -> int:
        """Count photos with optional filtering."""
        return await self._photo_repo.count(album_id=album_id)

    async def get_photos_pending_processing(self, limit: int = 100) -> list[Photo]:
        """Get photos that need processing."""
        # TODO: Implement find_pending_processing in PhotoRepository
        raise NotImplementedError("find_pending_processing not yet implemented")
