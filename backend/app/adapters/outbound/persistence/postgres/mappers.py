"""Mappers between domain entities and SQLAlchemy models."""

from datetime import datetime

from app.adapters.outbound.persistence.postgres.models import (
    AlbumModel,
    ConnectorModel,
    FaceClusterModel,
    FaceModel,
    PhotoModel,
)
from app.domain.entities.album import Album
from app.domain.entities.connector import Connector, ConnectorStatus, ConnectorType
from app.domain.entities.face import Face
from app.domain.entities.face_cluster import FaceCluster
from app.domain.entities.photo import Photo
from app.domain.value_objects import (
    AlbumId,
    BoundingBox,
    ConnectorId,
    ExifData,
    FaceClusterId,
    FaceId,
    GpsCoordinates,
    PhotoId,
    SceneClassification,
    SyncStats,
)


class PhotoMapper:
    """Maps between Photo domain entity and PhotoModel ORM."""

    @staticmethod
    def to_domain(model: PhotoModel) -> Photo:
        """Convert ORM model to domain entity."""
        # Reconstruct EXIF data if present
        exif = None
        if model.exif_data:
            gps = None
            if model.exif_data.get("gps_latitude") is not None:
                gps = GpsCoordinates(
                    latitude=model.exif_data["gps_latitude"],
                    longitude=model.exif_data["gps_longitude"],
                    altitude=model.exif_data.get("gps_altitude"),
                )
            exif = ExifData(
                camera_make=model.exif_data.get("camera_make"),
                camera_model=model.exif_data.get("camera_model"),
                lens_model=model.exif_data.get("lens_model"),
                focal_length=model.exif_data.get("focal_length"),
                aperture=model.exif_data.get("aperture"),
                iso=model.exif_data.get("iso"),
                shutter_speed=model.exif_data.get("shutter_speed"),
                flash=model.exif_data.get("flash"),
                orientation=model.exif_data.get("orientation"),
                gps=gps,
            )

        # Reconstruct scene classification if present
        scene_classification = None
        if model.scene_type is not None:
            scene_classification = SceneClassification(
                scene_type=model.scene_type,
                confidence=model.scene_confidence or 0.0,
                is_indoor=model.is_indoor,
            )

        return Photo(
            id=PhotoId(model.id),
            filename=model.filename,
            created_at=model.created_at,
            updated_at=model.updated_at,
            connector_type=model.connector_type,
            connector_id=model.connector_id,
            external_id=model.external_id,
            source_path=model.source_path,
            source_deleted=model.source_deleted,
            last_synced=model.last_synced,
            storage_path=model.storage_path,
            thumbnail_path=model.thumbnail_path,
            cached_thumbnail_path=model.cached_thumbnail_path,
            thumbnail_expires_at=model.thumbnail_expires_at,
            original_path=model.original_path,
            mime_type=model.mime_type,
            file_size=model.file_size,
            width=model.width,
            height=model.height,
            taken_at=model.taken_at,
            exif=exif,
            description=model.description,
            scene_classification=scene_classification,
            detected_objects=model.detected_objects or [],
            processing_status=model.processing_status,
            album_ids=[album.id for album in model.albums],
            face_ids=[face.id for face in model.faces],
        )

    @staticmethod
    def to_model(entity: Photo) -> PhotoModel:
        """Convert domain entity to ORM model."""
        # Serialize EXIF data
        exif_data = None
        if entity.exif:
            exif_data = {
                "camera_make": entity.exif.camera_make,
                "camera_model": entity.exif.camera_model,
                "lens_model": entity.exif.lens_model,
                "focal_length": entity.exif.focal_length,
                "aperture": entity.exif.aperture,
                "iso": entity.exif.iso,
                "shutter_speed": entity.exif.shutter_speed,
                "flash": entity.exif.flash,
                "orientation": entity.exif.orientation,
            }
            if entity.exif.gps:
                exif_data["gps_latitude"] = entity.exif.gps.latitude
                exif_data["gps_longitude"] = entity.exif.gps.longitude
                exif_data["gps_altitude"] = entity.exif.gps.altitude

        return PhotoModel(
            id=entity.id.value,
            filename=entity.filename,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            connector_type=entity.connector_type,
            connector_id=entity.connector_id,
            external_id=entity.external_id,
            source_path=entity.source_path,
            source_deleted=entity.source_deleted,
            last_synced=entity.last_synced,
            storage_path=entity.storage_path,
            thumbnail_path=entity.thumbnail_path,
            cached_thumbnail_path=entity.cached_thumbnail_path,
            thumbnail_expires_at=entity.thumbnail_expires_at,
            original_path=entity.original_path,
            mime_type=entity.mime_type,
            file_size=entity.file_size,
            width=entity.width,
            height=entity.height,
            taken_at=entity.taken_at,
            exif_data=exif_data,
            description=entity.description,
            scene_type=entity.scene_classification.scene_type if entity.scene_classification else None,
            scene_confidence=entity.scene_classification.confidence if entity.scene_classification else None,
            is_indoor=entity.scene_classification.is_indoor if entity.scene_classification else None,
            detected_objects=entity.detected_objects if entity.detected_objects else None,
            processing_status=entity.processing_status,
        )


class AlbumMapper:
    """Maps between Album domain entity and AlbumModel ORM."""

    @staticmethod
    def to_domain(model: AlbumModel) -> Album:
        """Convert ORM model to domain entity."""
        return Album(
            id=AlbumId(model.id),
            name=model.name,
            description=model.description,
            cover_photo_id=model.cover_photo_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            photo_ids=[photo.id for photo in model.photos],
        )

    @staticmethod
    def to_model(entity: Album) -> AlbumModel:
        """Convert domain entity to ORM model."""
        return AlbumModel(
            id=entity.id.value,
            name=entity.name,
            description=entity.description,
            cover_photo_id=entity.cover_photo_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class FaceMapper:
    """Maps between Face domain entity and FaceModel ORM."""

    @staticmethod
    def to_domain(model: FaceModel) -> Face:
        """Convert ORM model to domain entity."""
        return Face(
            id=FaceId(model.id),
            photo_id=model.photo_id,
            bbox=BoundingBox(
                x=model.bbox_x,
                y=model.bbox_y,
                width=model.bbox_width,
                height=model.bbox_height,
            ),
            cluster_id=model.cluster_id,
            crop_path=model.crop_path,
            quality_score=model.quality_score,
            detection_confidence=model.detection_confidence,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Face) -> FaceModel:
        """Convert domain entity to ORM model."""
        return FaceModel(
            id=entity.id.value,
            photo_id=entity.photo_id,
            bbox_x=entity.bbox.x,
            bbox_y=entity.bbox.y,
            bbox_width=entity.bbox.width,
            bbox_height=entity.bbox.height,
            cluster_id=entity.cluster_id,
            crop_path=entity.crop_path,
            quality_score=entity.quality_score,
            detection_confidence=entity.detection_confidence,
            created_at=entity.created_at,
        )


class FaceClusterMapper:
    """Maps between FaceCluster domain entity and FaceClusterModel ORM."""

    @staticmethod
    def to_domain(model: FaceClusterModel) -> FaceCluster:
        """Convert ORM model to domain entity."""
        return FaceCluster(
            id=FaceClusterId(model.id),
            name=model.name,
            representative_face_id=model.representative_face_id,
            face_ids=[face.id for face in model.faces],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: FaceCluster) -> FaceClusterModel:
        """Convert domain entity to ORM model."""
        return FaceClusterModel(
            id=entity.id.value,
            name=entity.name,
            representative_face_id=entity.representative_face_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class ConnectorMapper:
    """Maps between Connector domain entity and ConnectorModel ORM."""

    @staticmethod
    def to_domain(model: ConnectorModel) -> Connector:
        """Convert ORM model to domain entity."""
        # Reconstruct sync stats if present
        sync_stats = None
        if model.last_sync_stats:
            sync_stats = SyncStats(
                total_items=model.last_sync_stats.get("total_items", 0),
                indexed=model.last_sync_stats.get("indexed", 0),
                skipped=model.last_sync_stats.get("skipped", 0),
                failed=model.last_sync_stats.get("failed", 0),
                started_at=(
                    datetime.fromisoformat(model.last_sync_stats["started_at"])
                    if model.last_sync_stats.get("started_at")
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(model.last_sync_stats["completed_at"])
                    if model.last_sync_stats.get("completed_at")
                    else None
                ),
            )

        return Connector(
            id=ConnectorId(model.id),
            type=model.type,
            name=model.name,
            enabled=model.enabled,
            status=model.status,
            config=model.config,
            last_sync=model.last_sync,
            last_sync_stats=sync_stats,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Connector) -> ConnectorModel:
        """Convert domain entity to ORM model."""
        # Serialize sync stats using to_dict method
        # Note: We only store the basic fields in DB, not computed properties
        sync_stats_data = None
        if entity.last_sync_stats:
            full_dict = entity.last_sync_stats.to_dict()
            # Store only the core data fields, not computed properties
            sync_stats_data = {
                "total_items": full_dict["total_items"],
                "indexed": full_dict["indexed"],
                "skipped": full_dict["skipped"],
                "failed": full_dict["failed"],
                "started_at": full_dict["started_at"],
                "completed_at": full_dict["completed_at"],
            }

        return ConnectorModel(
            id=entity.id.value,
            type=entity.type,
            name=entity.name,
            enabled=entity.enabled,
            status=entity.status,
            config=entity.config,
            last_sync=entity.last_sync,
            last_sync_stats=sync_stats_data,
            error_message=entity.error_message,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
