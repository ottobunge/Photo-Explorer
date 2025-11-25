"""SQLAlchemy ORM models for PostgreSQL."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.entities.connector import ConnectorStatus, ConnectorType


class Base(DeclarativeBase):
    """Base class for all ORM models."""



# Association table for Photo <-> Album many-to-many relationship
photo_album_association = Table(
    "photo_album",
    Base.metadata,
    Column(
        "photo_id",
        PG_UUID(as_uuid=True),
        ForeignKey("photos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "album_id",
        PG_UUID(as_uuid=True),
        ForeignKey("albums.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class PhotoModel(Base):
    """SQLAlchemy model for Photo entity."""

    __tablename__ = "photos"

    # Primary key
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Basic info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Connector reference
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    connector_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("connectors.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Storage paths
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cached_thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    thumbnail_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Legacy field
    original_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Metadata
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    # EXIF data (stored as JSON)
    exif_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # AI-generated content
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    scene_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scene_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_indoor: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    detected_objects: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )

    # Relationships
    connector: Mapped["ConnectorModel | None"] = relationship(back_populates="photos")
    albums: Mapped[list["AlbumModel"]] = relationship(
        secondary=photo_album_association, back_populates="photos"
    )
    faces: Mapped[list["FaceModel"]] = relationship(
        back_populates="photo", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_photos_connector_id", "connector_id"),
        Index("ix_photos_created_at", "created_at"),
        Index("ix_photos_connector_type", "connector_type"),
        Index("ix_photos_source_path", "source_path"),
        # Composite index for external photo lookups (added in migration 0003)
        Index("ix_photos_external_id_connector_id", "external_id", "connector_id"),
        {"comment": "Photos table with connector support"},
    )


class AlbumModel(Base):
    """SQLAlchemy model for Album entity."""

    __tablename__ = "albums"

    # Primary key
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Cover photo
    cover_photo_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("photos.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    photos: Mapped[list["PhotoModel"]] = relationship(
        secondary=photo_album_association, back_populates="albums"
    )


class FaceModel(Base):
    """SQLAlchemy model for Face entity."""

    __tablename__ = "faces"

    # Primary key
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Photo reference
    photo_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("photos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Cluster reference
    cluster_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("face_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Bounding box (stored as JSON for flexibility)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)

    # Storage
    crop_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Quality metrics
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    photo: Mapped["PhotoModel"] = relationship(back_populates="faces")
    cluster: Mapped["FaceClusterModel | None"] = relationship(back_populates="faces")


class FaceClusterModel(Base):
    """SQLAlchemy model for FaceCluster entity."""

    __tablename__ = "face_clusters"

    # Primary key
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Name (user-assigned)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Representative face
    representative_face_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    faces: Mapped[list["FaceModel"]] = relationship(back_populates="cluster")


class ConnectorModel(Base):
    """SQLAlchemy model for Connector entity."""

    __tablename__ = "connectors"

    # Primary key
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Basic info - use values_callable to match PostgreSQL enum values
    type: Mapped[ConnectorType] = mapped_column(
        Enum(
            ConnectorType,
            name="connectortype",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[ConnectorStatus] = mapped_column(
        Enum(
            ConnectorStatus,
            name="connectorstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ConnectorStatus.DISCONNECTED,
    )

    # Configuration (stored as JSON)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Sync state
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    photos: Mapped[list["PhotoModel"]] = relationship(back_populates="connector")


class OAuthTokenModel(Base):
    """SQLAlchemy model for encrypted OAuth token storage."""

    __tablename__ = "oauth_tokens"

    # Primary key - using connector_type as the key
    connector_type: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Encrypted token data (JSON encrypted with Fernet)
    encrypted_data: Mapped[str] = mapped_column(String(4096), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class TaskExecutionModel(Base):
    """SQLAlchemy model for task execution tracking (idempotency)."""

    __tablename__ = "task_executions"

    # Primary key - Celery task ID
    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Task info
    task_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    # Retry tracking
    retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Error and result
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)

    # Context (JSON)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("ix_task_executions_name_status", "task_name", "status"),
        {"comment": "Task execution tracking for idempotency"},
    )
