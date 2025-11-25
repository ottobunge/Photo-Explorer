"""Test data factories for creating domain entities in tests."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.domain.entities import Album, Face, Photo, Connector
from app.domain.entities.connector import ConnectorType, ConnectorStatus
from app.domain.value_objects import (
    AlbumId,
    BoundingBox,
    Embedding,
    ExifData,
    FaceId,
    PhotoId,
    ConnectorId,
)


class PhotoFactory:
    """Factory for creating Photo test instances."""

    @staticmethod
    def create(
        id: Optional[UUID] = None,
        filename: str = "test_photo.jpg",
        created_at: Optional[datetime] = None,
        connector_type: str = "local",
        connector_id: Optional[UUID] = None,
        storage_path: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        mime_type: str = "image/jpeg",
        width: int = 1920,
        height: int = 1080,
        taken_at: Optional[datetime] = None,
        processing_status: str = "pending",
        **kwargs,
    ) -> Photo:
        """Create a Photo entity with sensible defaults."""
        photo_id = id or uuid4()
        now = created_at or datetime.utcnow()

        return Photo(
            id=PhotoId(photo_id),
            filename=filename,
            created_at=now,
            updated_at=now,
            connector_type=connector_type,
            connector_id=connector_id,
            storage_path=storage_path or f"photos/{photo_id}.jpg",
            thumbnail_path=thumbnail_path or f"thumbnails/{photo_id}.jpg",
            mime_type=mime_type,
            file_size=kwargs.get("file_size", 1024000),
            width=width,
            height=height,
            taken_at=taken_at or now,
            processing_status=processing_status,
            album_ids=kwargs.get("album_ids", []),
            face_ids=kwargs.get("face_ids", []),
            exif=kwargs.get("exif"),
            description=kwargs.get("description"),
            scene_classification=kwargs.get("scene_classification"),
            detected_objects=kwargs.get("detected_objects", []),
            source_path=kwargs.get("source_path"),
            source_deleted=kwargs.get("source_deleted", False),
            last_synced=kwargs.get("last_synced"),
            cached_thumbnail_path=kwargs.get("cached_thumbnail_path"),
            thumbnail_expires_at=kwargs.get("thumbnail_expires_at"),
            external_id=kwargs.get("external_id"),
        )

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[Photo]:
        """Create multiple photos with unique IDs."""
        return [
            PhotoFactory.create(filename=f"photo_{i}.jpg", **kwargs)
            for i in range(count)
        ]


class AlbumFactory:
    """Factory for creating Album test instances."""

    @staticmethod
    def create(
        id: Optional[UUID] = None,
        name: str = "Test Album",
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        photo_ids: Optional[list[UUID]] = None,
        cover_photo_id: Optional[UUID] = None,
    ) -> Album:
        """Create an Album entity with sensible defaults."""
        album_id = id or uuid4()
        now = created_at or datetime.utcnow()

        return Album(
            id=AlbumId(album_id),
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            photo_ids=photo_ids or [],
            cover_photo_id=cover_photo_id,
        )

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[Album]:
        """Create multiple albums with unique names."""
        return [
            AlbumFactory.create(name=f"Album {i}", **kwargs)
            for i in range(count)
        ]


class FaceFactory:
    """Factory for creating Face test instances."""

    @staticmethod
    def create(
        id: Optional[UUID] = None,
        photo_id: Optional[UUID] = None,
        bounding_box: Optional[BoundingBox] = None,
        confidence: float = 0.95,
        embedding: Optional[Embedding] = None,
        cluster_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
    ) -> Face:
        """Create a Face entity with sensible defaults."""
        face_id = id or uuid4()
        now = created_at or datetime.utcnow()

        # Default bounding box
        if bounding_box is None:
            bounding_box = BoundingBox(x=100, y=100, width=200, height=200)

        # Default embedding (512-dim for InsightFace)
        if embedding is None:
            embedding = Embedding([0.0] * 512)

        return Face(
            id=FaceId(face_id),
            photo_id=photo_id or uuid4(),
            bounding_box=bounding_box,
            confidence=confidence,
            embedding=embedding,
            cluster_id=cluster_id,
            created_at=now,
        )

    @staticmethod
    def create_batch(count: int, photo_id: UUID, **kwargs) -> list[Face]:
        """Create multiple faces for a photo."""
        return [
            FaceFactory.create(photo_id=photo_id, **kwargs)
            for i in range(count)
        ]


class ConnectorFactory:
    """Factory for creating Connector test instances."""

    @staticmethod
    def create_local_folder(
        id: Optional[UUID] = None,
        name: str = "Test Local Folder",
        path: str = "/test/photos",
        recursive: bool = True,
        watch: bool = False,
        auto_album: bool = False,
    ) -> Connector:
        """Create a local folder connector."""
        connector = Connector.create_local(
            path=path,
            name=name,
            recursive=recursive,
            watch=watch,
            auto_album=auto_album,
        )
        if id:
            connector.id = ConnectorId(id)
        return connector

    @staticmethod
    def create_google_photos(
        id: Optional[UUID] = None,
        name: str = "Test Google Photos",
    ) -> Connector:
        """Create a Google Photos connector."""
        connector = Connector.create_google_photos(name=name)
        if id:
            connector.id = ConnectorId(id)
        return connector

    @staticmethod
    def create_upload(
        id: Optional[UUID] = None,
        name: str = "Test Upload",
        upload_path: str = "/uploads",
    ) -> Connector:
        """Create an upload connector."""
        connector = Connector.create_upload(upload_path=upload_path)
        if id and name != "Test Upload":
            connector.name = name
        if id:
            connector.id = ConnectorId(id)
        return connector


class EmbeddingFactory:
    """Factory for creating test embeddings."""

    @staticmethod
    def create_clip_embedding(dimension: int = 768) -> Embedding:
        """Create a CLIP embedding with specified dimensions."""
        # Create a normalized random-like vector
        import math
        values = [math.sin(i * 0.1) for i in range(dimension)]
        # Normalize
        magnitude = math.sqrt(sum(v * v for v in values))
        normalized = [v / magnitude for v in values]
        return Embedding(normalized)

    @staticmethod
    def create_face_embedding(dimension: int = 512) -> Embedding:
        """Create a face embedding (InsightFace, 512-dim)."""
        import math
        values = [math.cos(i * 0.1) for i in range(dimension)]
        # Normalize
        magnitude = math.sqrt(sum(v * v for v in values))
        normalized = [v / magnitude for v in values]
        return Embedding(normalized)

    @staticmethod
    def create_similar_embedding(base: Embedding, noise: float = 0.1) -> Embedding:
        """Create an embedding similar to the base with some noise."""
        import random
        import math

        values = base.to_list()
        noisy = [v + random.uniform(-noise, noise) for v in values]

        # Normalize
        magnitude = math.sqrt(sum(v * v for v in noisy))
        normalized = [v / magnitude for v in noisy]
        return Embedding(normalized)
