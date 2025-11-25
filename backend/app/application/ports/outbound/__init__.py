"""Outbound ports - Repository and service interfaces."""

from app.application.ports.outbound.album_repository import AlbumRepository
from app.application.ports.outbound.config_storage import ConfigStorage
from app.application.ports.outbound.connector_repository import ConnectorRepository
from app.application.ports.outbound.face_repository import FaceRepository
from app.application.ports.outbound.file_storage import FileStorage
from app.application.ports.outbound.ml_services import (
    DetectedFace,
    DetectedObjectInfo,
    ImageAnalysis,
    MLServices,
)
from app.application.ports.outbound.photo_repository import PhotoRepository
from app.application.ports.outbound.photo_source import PhotoSource, RemotePhotoMetadata
from app.application.ports.outbound.token_storage import OAuthTokens, TokenStorage
from app.application.ports.outbound.vector_store import VectorStore

__all__ = [
    # Repositories
    "PhotoRepository",
    "AlbumRepository",
    "FaceRepository",
    "ConnectorRepository",
    # Storage
    "VectorStore",
    "FileStorage",
    "TokenStorage",
    "OAuthTokens",
    "ConfigStorage",
    # ML Services
    "MLServices",
    "DetectedFace",
    "DetectedObjectInfo",
    "ImageAnalysis",
    # Remote sources
    "PhotoSource",
    "RemotePhotoMetadata",
]
