"""Domain value objects - Immutable objects representing domain concepts."""

from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.embedding import Embedding
from app.domain.value_objects.exif_data import ExifData, GpsCoordinates
from app.domain.value_objects.ids import AlbumId, ConnectorId, FaceClusterId, FaceId, PhotoId
from app.domain.value_objects.scene_classification import SceneClassification

__all__ = [
    "PhotoId",
    "AlbumId",
    "FaceId",
    "FaceClusterId",
    "ConnectorId",
    "BoundingBox",
    "Embedding",
    "ExifData",
    "GpsCoordinates",
    "SceneClassification",
]
