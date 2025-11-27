"""ConnectorService - Business logic layer for connector operations."""

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from app.application.ports.outbound import (
    ConnectorRepository,
    FileStorage,
    PhotoRepository,
    VectorStore,
)
from app.application.services.constants import MAX_PHOTO_FETCH_LIMIT
from app.application.services.types import GooglePhotosConfigDict, LocalConnectorConfigDict
from app.config import get_settings
from app.domain.entities import Photo
from app.domain.entities.connector import Connector, ConnectorType

logger = logging.getLogger(__name__)


class ConnectorService:
    """
    Service layer for connector business logic.

    Responsibilities:
    - Enforce domain model rules (use enable/disable methods)
    - Add path security validation (prevent traversal attacks)
    - Transaction management for multi-step operations
    - Use bulk delete for photo deletion
    """

    def __init__(
        self,
        connector_repo: ConnectorRepository,
        photo_repo: PhotoRepository,
        file_storage: FileStorage,
        vector_store: VectorStore,
    ) -> None:
        """Initialize service with repository dependencies."""
        self._connector_repo = connector_repo
        self._photo_repo = photo_repo
        self._file_storage = file_storage
        self._vector_store = vector_store

    async def create_local_connector(
        self,
        path: str,
        name: Optional[str] = None,
        recursive: bool = True,
        watch: bool = False,
        auto_album: bool = False,
    ) -> Connector:
        """
        Create a local folder connector with path validation.

        Args:
            path: Filesystem path to index
            name: Optional connector name (defaults to directory name)
            recursive: Whether to recursively scan subdirectories
            watch: Whether to watch for file changes
            auto_album: Whether to automatically create albums from folders

        Returns:
            Created connector entity

        Raises:
            ValueError: If path is invalid, not allowed, or already exists
        """
        # Validate and resolve path (includes security checks)
        validated_path = self._validate_local_path(path)

        # Check for duplicate path
        existing = await self._connector_repo.find_by_path(str(validated_path))
        if existing:
            raise ValueError(f"Connector already exists for path: {validated_path}")

        # Generate default name from directory if not provided
        connector_name = name or validated_path.name or "Local Folder"

        # Create connector using domain factory method
        connector = Connector.create_local(
            path=str(validated_path),
            name=connector_name,
            recursive=recursive,
            watch=watch,
            auto_album=auto_album,
        )

        # Persist and return
        return await self._connector_repo.save(connector)

    async def create_google_photos_connector(
        self, name: str = "Google Photos", email: Optional[str] = None
    ) -> Connector:
        """
        Create a Google Photos connector.

        Args:
            name: Connector name
            email: Optional email to store in config

        Returns:
            Created connector entity
        """
        connector = Connector.create_google_photos(name=name)
        # Set connected status and email config if provided
        connector.set_connected()
        if email:
            connector.config["email"] = email
        return await self._connector_repo.save(connector)

    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        config: Optional[dict[str, str | int | bool | list[str]]] = None,
    ) -> Connector:
        """
        Update connector using domain methods.

        Args:
            connector_id: Connector to update
            name: Optional new name
            enabled: Optional enabled state (uses enable/disable methods)
            config: Optional configuration updates (uses update_config method)

        Returns:
            Updated connector entity

        Raises:
            ValueError: If connector not found or validation fails
        """
        connector = await self._connector_repo.find_by_id(connector_id)
        if not connector:
            raise ValueError(f"Connector not found: {connector_id}")

        # Update name directly (simple field)
        if name is not None:
            connector.name = name
            connector._touch()  # Update timestamp

        # Use domain methods for enabled state changes
        if enabled is not None:
            if enabled:
                connector.enable()
            else:
                connector.disable()

        # Use domain method for config updates with path validation
        if config is not None:
            # For local connectors, validate path if it's being changed
            if connector.type == ConnectorType.LOCAL and "path" in config:
                new_path_value = config["path"]
                # Type guard - path must be a string
                if not isinstance(new_path_value, str):
                    raise ValueError("Path must be a string")
                # Validate the new path
                validated_path = self._validate_local_path(new_path_value)
                # Update config with validated path
                config["path"] = str(validated_path)

            connector.update_config(config)

        # Persist and return
        return await self._connector_repo.save(connector)

    async def delete_connector(
        self,
        connector_id: UUID,
        delete_photos: bool = True,
    ) -> int:
        """
        Delete connector and all associated photos.

        By default, deletes all photos indexed from this connector.
        This ensures no orphaned photos remain in the system.

        Uses transaction management to ensure atomicity:
        - All operations succeed together, or all are rolled back
        - Prevents partial deletions and data corruption

        Args:
            connector_id: Connector to delete
            delete_photos: If True (default), delete all associated photos using bulk delete.
                          Set to False to orphan photos (not recommended).

        Returns:
            Number of photos deleted (0 if delete_photos=False)

        Raises:
            ValueError: If connector not found
        """
        connector = await self._connector_repo.find_by_id(connector_id)
        if not connector:
            raise ValueError(f"Connector not found: {connector_id}")

        # Delete photos and clean up associated resources if requested
        photo_count = 0
        if delete_photos:
            # First, get all photos for this connector to clean up files/embeddings
            photos = await self._photo_repo.find_all(
                connector_id=connector_id, limit=MAX_PHOTO_FETCH_LIMIT
            )
            photo_count = len(photos)

            # Clean up storage files and embeddings for each photo
            # Note: File cleanup is best-effort - failures logged but don't block deletion
            for photo in photos:
                try:
                    # Delete photo file if it exists
                    if photo.storage_path:
                        await self._file_storage.delete_file(photo.storage_path)

                    # Delete thumbnail if it exists
                    if photo.thumbnail_path:
                        await self._file_storage.delete_file(photo.thumbnail_path)

                    # Delete cached thumbnail if it exists
                    if photo.cached_thumbnail_path:
                        await self._file_storage.delete_file(photo.cached_thumbnail_path)

                    # Delete CLIP embedding from vector store
                    try:
                        await self._vector_store.delete_photo_embedding(photo.id.value)
                    except Exception as e:
                        # Log unexpected errors instead of silencing them
                        # Expected: embedding not found (404), acceptable to ignore
                        # Unexpected: connection errors, permission errors, etc.
                        logger.warning(
                            f"Error deleting photo embedding {photo.id.value}: {type(e).__name__}: {e}"
                        )

                    # Delete face embeddings from vector store
                    for face_id in photo.face_ids:
                        try:
                            await self._vector_store.delete_face_embedding(face_id)
                        except Exception as e:
                            # Log unexpected errors instead of silencing them
                            logger.warning(
                                f"Error deleting face embedding {face_id}: {type(e).__name__}: {e}"
                            )

                except Exception as cleanup_err:
                    # Log error but continue with deletion
                    logger.warning(
                        f"Failed to clean up resources for photo {photo.id.value}: {cleanup_err}"
                    )

            # Now bulk delete from database
            await self._photo_repo.delete_bulk_by_connector(connector_id)

        # Delete the connector (photos are orphaned if delete_photos=False)
        await self._connector_repo.delete(connector_id)

        # Note: Transaction commit/rollback handled by the caller (usually the route)
        # via the db_session dependency

        return photo_count

    async def get_connector(self, connector_id: UUID) -> Optional[Connector]:
        """
        Get a connector by ID.

        Args:
            connector_id: Connector unique identifier

        Returns:
            Connector entity or None if not found
        """
        return await self._connector_repo.find_by_id(connector_id)

    async def list_connectors(
        self,
        connector_type: Optional[ConnectorType] = None,
        status: Optional[str] = None,
    ) -> list[Connector]:
        """
        List all connectors with optional filtering.

        Args:
            connector_type: Optional filter by connector type
            status: Optional filter by connector status

        Returns:
            List of connector entities matching filters
        """
        connectors = await self._connector_repo.find_all()

        # Apply filters if provided
        if connector_type is not None:
            connectors = [c for c in connectors if c.type == connector_type]

        if status is not None:
            from app.domain.entities.connector import ConnectorStatus as StatusEnum

            connectors = [c for c in connectors if c.status == status]

        return connectors

    async def get_connector_photos(
        self,
        connector_id: UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Photo], int]:
        """
        Get paginated photos for a connector.

        Args:
            connector_id: Connector unique identifier
            page: Page number (1-indexed)
            per_page: Number of photos per page

        Returns:
            Tuple of (photos list, total count)

        Raises:
            ValueError: If connector not found
        """
        # Verify connector exists
        connector = await self._connector_repo.find_by_id(connector_id)
        if not connector:
            raise ValueError(f"Connector not found: {connector_id}")

        # Calculate pagination offset
        offset = (page - 1) * per_page

        # Fetch paginated photos and total count
        photos = await self._photo_repo.find_all(
            connector_id=connector_id, limit=per_page, offset=offset
        )
        total = await self._photo_repo.count(connector_id=connector_id)

        return photos, total

    async def disconnect_google_photos_connectors(self) -> int:
        """
        Disconnect all Google Photos connectors using domain methods.

        Returns:
            Number of connectors disconnected

        Note:
            This does NOT delete stored tokens - caller must handle token cleanup
        """
        connectors = await self._connector_repo.find_all()
        google_photos_connectors = [c for c in connectors if c.type == ConnectorType.GOOGLE_PHOTOS]

        for connector in google_photos_connectors:
            # Use domain method instead of direct mutation
            connector.set_disconnected()
            await self._connector_repo.save(connector)

        return len(google_photos_connectors)

    def _validate_local_path(self, path: str) -> Path:
        """
        Validate path is safe and within allowed directories.

        Security validation to prevent path traversal attacks:
        - Resolves symlinks to real paths
        - Checks path is within allowed base directories
        - Ensures path exists and is a directory

        Args:
            path: Path to validate

        Returns:
            Resolved, validated Path object

        Raises:
            ValueError: If path is invalid, doesn't exist, or not allowed
        """
        settings = get_settings()

        # Use existing config validation (checks allowed base paths)
        is_allowed, error_msg = settings.is_path_allowed(path)
        if not is_allowed:
            raise ValueError(error_msg)

        # Resolve to absolute path and follow symlinks
        path_obj = Path(path).resolve()

        # Validate path exists
        if not path_obj.exists():
            raise ValueError(f"Path does not exist: {path}")

        # Validate path is a directory
        if not path_obj.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        return path_obj
