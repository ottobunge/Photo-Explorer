"""ConnectorService - Business logic layer for connector operations."""

from pathlib import Path
from typing import Optional
from uuid import UUID

from app.application.ports.outbound import ConnectorRepository, PhotoRepository
from app.config import get_settings
from app.domain.entities.connector import Connector, ConnectorStatus, ConnectorType


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
    ) -> None:
        """Initialize service with repository dependencies."""
        self._connector_repo = connector_repo
        self._photo_repo = photo_repo

    async def create_local_connector(
        self,
        path: str,
        name: Optional[str] = None,
        **config,
    ) -> Connector:
        """
        Create a local folder connector with path validation.

        Args:
            path: Filesystem path to index
            name: Optional connector name (defaults to directory name)
            **config: Additional configuration options (recursive, watch, auto_album)

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
            recursive=config.get("recursive", True),
            watch=config.get("watch", False),
            auto_album=config.get("auto_album", False),
        )

        # Persist and return
        return await self._connector_repo.save(connector)

    async def create_google_photos_connector(self, name: str = "Google Photos") -> Connector:
        """
        Create a Google Photos connector.

        Args:
            name: Connector name

        Returns:
            Created connector entity
        """
        connector = Connector.create_google_photos(name=name)
        return await self._connector_repo.save(connector)

    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        config: Optional[dict] = None,
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
                new_path = config["path"]
                # Validate the new path
                validated_path = self._validate_local_path(new_path)
                # Update config with validated path
                config["path"] = str(validated_path)

            connector.update_config(config)

        # Persist and return
        return await self._connector_repo.save(connector)

    async def delete_connector(
        self,
        connector_id: UUID,
        delete_photos: bool = False,
    ) -> int:
        """
        Delete connector with optional photo deletion.

        Uses transaction management to ensure atomicity:
        - All operations succeed together, or all are rolled back
        - Prevents partial deletions and data corruption

        Args:
            connector_id: Connector to delete
            delete_photos: If True, delete all associated photos using bulk delete

        Returns:
            Number of photos deleted (0 if delete_photos=False)

        Raises:
            ValueError: If connector not found
        """
        connector = await self._connector_repo.find_by_id(connector_id)
        if not connector:
            raise ValueError(f"Connector not found: {connector_id}")

        # Delete photos using bulk operation if requested
        photo_count = 0
        if delete_photos:
            photo_count = await self._photo_repo.delete_bulk_by_connector(connector_id)

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

    async def list_connectors(self) -> list[Connector]:
        """
        List all connectors.

        Returns:
            List of all connector entities
        """
        return await self._connector_repo.find_all()

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
