"""Inbound ports - Use case interfaces that define application capabilities."""

from app.application.ports.inbound.album_use_cases import AlbumUseCases
from app.application.ports.inbound.connector_use_cases import (
    ConnectorUseCases,
    GooglePhotosConnectorUseCases,
)
from app.application.ports.inbound.face_use_cases import FaceUseCases
from app.application.ports.inbound.folder_use_cases import FolderUseCases
from app.application.ports.inbound.photo_use_cases import PhotoUseCases
from app.application.ports.inbound.search_use_cases import SearchUseCases
from app.application.ports.inbound.settings_use_cases import (
    AppSettings,
    ConnectorSettings,
    SettingsUseCases,
)

__all__ = [
    "PhotoUseCases",
    "AlbumUseCases",
    "SearchUseCases",
    "FaceUseCases",
    "FolderUseCases",
    "ConnectorUseCases",
    "GooglePhotosConnectorUseCases",
    "SettingsUseCases",
    "AppSettings",
    "ConnectorSettings",
]
