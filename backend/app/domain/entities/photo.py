"""Photo aggregate root entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.domain.value_objects import ExifData, PhotoId, SceneClassification


@dataclass
class Photo:
    """
    Photo aggregate root.

    Represents a photo in the system with all its metadata,
    AI-generated descriptions, and detected faces.

    Photos can come from different sources (connectors):
    - local: stored on the local filesystem
    - google_photos: indexed from Google Photos (not stored locally)
    """

    id: PhotoId
    filename: str
    created_at: datetime

    # Connector reference (where the photo comes from)
    connector_type: str = "local"  # "local", "google_photos", etc.
    connector_id: Optional[UUID] = None  # Reference to Connector entity
    external_id: Optional[str] = None  # ID in the source system
    source_path: Optional[str] = None  # Original path/URL in source
    source_deleted: bool = False  # Source no longer exists
    last_synced: Optional[datetime] = None

    # Storage paths (for local or cached files)
    storage_path: Optional[str] = None  # Local storage (if downloaded)
    thumbnail_path: Optional[str] = None
    cached_thumbnail_path: Optional[str] = None  # Cached thumbnail for remote
    thumbnail_expires_at: Optional[datetime] = None

    # Optional metadata
    original_path: Optional[str] = None  # Deprecated: use source_path
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    taken_at: Optional[datetime] = None

    # EXIF data
    exif: Optional[ExifData] = None

    # AI-generated content
    description: Optional[str] = None
    scene_classification: Optional[SceneClassification] = None
    detected_objects: list[str] = field(default_factory=list)

    # Processing status
    processing_status: str = "pending"
    updated_at: Optional[datetime] = None

    # Relationships (IDs only to maintain aggregate boundaries)
    album_ids: list[UUID] = field(default_factory=list)
    face_ids: list[UUID] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        filename: str,
        storage_path: Optional[str] = None,
        original_path: Optional[str] = None,
        album_id: Optional[UUID] = None,
        connector_type: str = "local",
        connector_id: Optional[UUID] = None,
    ) -> "Photo":
        """Factory method to create a new local photo.

        Args:
            filename: The photo's filename
            storage_path: Path where photo is stored locally
            original_path: Original source path (deprecated, use source_path)
            album_id: Optional album to add the photo to
            connector_type: Type of connector ("local", "upload", "google_photos")
            connector_id: Optional connector ID to associate this photo with

        Returns:
            New Photo instance
        """
        now = datetime.now(timezone.utc)
        album_ids = [album_id] if album_id else []

        return cls(
            id=PhotoId(uuid4()),
            filename=filename,
            storage_path=storage_path,
            source_path=original_path or storage_path,
            original_path=original_path,
            connector_type=connector_type,
            connector_id=connector_id,
            created_at=now,
            updated_at=now,
            album_ids=album_ids,
        )

    @classmethod
    def create_from_connector(
        cls,
        filename: str,
        connector_type: str,
        connector_id: UUID,
        external_id: str,
        source_path: Optional[str] = None,
    ) -> "Photo":
        """Factory method to create a photo from a remote connector."""
        now = datetime.now(timezone.utc)

        return cls(
            id=PhotoId(uuid4()),
            filename=filename,
            connector_type=connector_type,
            connector_id=connector_id,
            external_id=external_id,
            source_path=source_path,
            last_synced=now,
            created_at=now,
            updated_at=now,
        )

    def add_to_album(self, album_id: UUID) -> None:
        """Add this photo to an album."""
        if album_id not in self.album_ids:
            self.album_ids.append(album_id)
            self._touch()

    def remove_from_album(self, album_id: UUID) -> None:
        """Remove this photo from an album."""
        if album_id in self.album_ids:
            self.album_ids.remove(album_id)
            self._touch()

    def set_metadata(
        self,
        mime_type: Optional[str] = None,
        file_size: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        taken_at: Optional[datetime] = None,
        exif: Optional[ExifData] = None,
    ) -> None:
        """Set photo metadata extracted from the file."""
        self.mime_type = mime_type
        self.file_size = file_size
        self.width = width
        self.height = height
        self.taken_at = taken_at
        self.exif = exif
        self._touch()

    def set_ai_analysis(
        self,
        description: Optional[str] = None,
        scene_classification: Optional[SceneClassification] = None,
        detected_objects: Optional[list[str]] = None,
    ) -> None:
        """Set AI-generated analysis results."""
        if description is not None:
            self.description = description
        if scene_classification is not None:
            self.scene_classification = scene_classification
        if detected_objects is not None:
            self.detected_objects = detected_objects
        self._touch()

    def set_processing_status(self, status: str) -> None:
        """Update processing status."""
        valid_statuses = {"pending", "processing", "completed", "failed"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        self.processing_status = status
        self._touch()

    def add_face(self, face_id: UUID) -> None:
        """Register a detected face."""
        if face_id not in self.face_ids:
            self.face_ids.append(face_id)
            self._touch()

    def remove_face(self, face_id: UUID) -> None:
        """Remove a detected face."""
        if face_id in self.face_ids:
            self.face_ids.remove(face_id)
            self._touch()

    @property
    def is_processed(self) -> bool:
        """Check if the photo has been fully processed."""
        return self.processing_status == "completed"

    @property
    def is_indoor(self) -> Optional[bool]:
        """Check if the photo was taken indoors."""
        if self.scene_classification:
            return self.scene_classification.is_indoor
        return None

    @property
    def is_remote(self) -> bool:
        """Check if this photo is from a remote source."""
        return self.connector_type != "local"

    @property
    def is_local(self) -> bool:
        """Check if this photo is stored locally."""
        return self.connector_type == "local"

    @property
    def has_local_file(self) -> bool:
        """Check if a local file exists for this photo."""
        return self.storage_path is not None

    def mark_source_deleted(self) -> None:
        """Mark the source as deleted (no longer exists in remote)."""
        self.source_deleted = True
        self._touch()

    def update_sync(self) -> None:
        """Update the last synced timestamp."""
        self.last_synced = datetime.now(timezone.utc)
        self.source_deleted = False
        self._touch()

    def set_cached_thumbnail(self, path: str, expires_at: datetime) -> None:
        """Set the cached thumbnail path and expiration."""
        self.cached_thumbnail_path = path
        self.thumbnail_expires_at = expires_at
        self._touch()

    @property
    def cached_thumbnail_valid(self) -> bool:
        """Check if the cached thumbnail is still valid."""
        if not self.cached_thumbnail_path or not self.thumbnail_expires_at:
            return False
        return datetime.now(timezone.utc) < self.thumbnail_expires_at

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)
