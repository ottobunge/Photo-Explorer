"""Connector aggregate root entity."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from app.domain.value_objects import ConnectorId, SyncStats


class ConnectorType(str, Enum):
    """Supported connector types."""

    GOOGLE_PHOTOS = "google_photos"
    LOCAL = "local"
    UPLOAD = "upload"  # Default upload folder connector


class ConnectorStatus(str, Enum):
    """Connector connection status."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"


@dataclass
class Connector:
    """
    Connector aggregate root.

    Represents a connection to an external photo source
    (Google Photos, local folder, etc.)
    """

    id: ConnectorId
    type: ConnectorType
    name: str
    enabled: bool
    status: ConnectorStatus
    created_at: datetime

    # Configuration (type-specific)
    config: dict = field(default_factory=dict)

    # Sync state
    last_sync: Optional[datetime] = None
    last_sync_stats: Optional[SyncStats] = None
    error_message: Optional[str] = None

    updated_at: Optional[datetime] = None

    @classmethod
    def create_google_photos(cls, name: str = "Google Photos") -> "Connector":
        """Factory method for Google Photos connector."""
        now = datetime.utcnow()
        return cls(
            id=ConnectorId(uuid4()),
            type=ConnectorType.GOOGLE_PHOTOS,
            name=name,
            enabled=True,
            status=ConnectorStatus.DISCONNECTED,
            config={
                "sync_interval_hours": 6,
                "include_albums": "all",
            },
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def create_local(
        cls,
        path: str,
        name: Optional[str] = None,
        recursive: bool = True,
        watch: bool = True,
        auto_album: bool = False,
    ) -> "Connector":
        """Factory method for local folder connector."""
        now = datetime.utcnow()
        return cls(
            id=ConnectorId(uuid4()),
            type=ConnectorType.LOCAL,
            name=name or path,
            enabled=True,
            status=ConnectorStatus.CONNECTED,  # Local is always "connected"
            config={
                "path": path,
                "recursive": recursive,
                "watch": watch,
                "auto_album": auto_album,
            },
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def create_upload(cls, upload_path: str) -> "Connector":
        """Factory method for the default upload folder connector.

        This is a special built-in connector that handles uploaded photos.
        There should only be one of these per installation.
        """
        now = datetime.utcnow()
        return cls(
            id=ConnectorId(uuid4()),
            type=ConnectorType.UPLOAD,
            name="Uploads",
            enabled=True,
            status=ConnectorStatus.CONNECTED,
            config={
                "path": upload_path,
                "is_default": True,
            },
            created_at=now,
            updated_at=now,
        )

    def set_connected(self) -> None:
        """Mark connector as connected."""
        self.status = ConnectorStatus.CONNECTED
        self.error_message = None
        self._touch()

    def set_disconnected(self) -> None:
        """Mark connector as disconnected."""
        self.status = ConnectorStatus.DISCONNECTED
        self._touch()

    def set_syncing(self) -> None:
        """Mark connector as currently syncing."""
        self.status = ConnectorStatus.SYNCING
        self._touch()

    def set_error(self, message: str) -> None:
        """Mark connector as having an error."""
        self.status = ConnectorStatus.ERROR
        self.error_message = message
        self._touch()

    def record_sync(self, stats: SyncStats) -> None:
        """Record completion of a sync operation."""
        self.last_sync = datetime.utcnow()
        self.last_sync_stats = stats
        if stats.failed == 0:
            self.status = ConnectorStatus.CONNECTED
            self.error_message = None
        else:
            self.status = ConnectorStatus.ERROR
            self.error_message = f"{stats.failed} items failed to sync"
        self._touch()

    def update_config(self, config: dict) -> None:
        """Update connector configuration."""
        self.config.update(config)
        self._touch()

    def enable(self) -> None:
        """Enable the connector."""
        self.enabled = True
        self._touch()

    def disable(self) -> None:
        """Disable the connector."""
        self.enabled = False
        self._touch()

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote connector."""
        return self.type not in (ConnectorType.LOCAL, ConnectorType.UPLOAD)

    @property
    def path(self) -> Optional[str]:
        """Get the path for local/upload connectors."""
        if self.type in (ConnectorType.LOCAL, ConnectorType.UPLOAD):
            return self.config.get("path")
        return None

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
