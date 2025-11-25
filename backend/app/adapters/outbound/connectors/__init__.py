"""Connector adapters for external photo sources."""

from app.adapters.outbound.connectors.folder_watcher import (
    FolderWatcher,
    PhotoFileEventHandler,
    get_folder_watcher,
    setup_watcher_callbacks,
)
from app.adapters.outbound.connectors.google_photos import (
    GooglePhotosClient,
    GooglePhotosPickerClient,
    PickerMediaItem,
    PickerSession,
)
from app.adapters.outbound.connectors.local_folder import (
    SUPPORTED_EXTENSIONS,
    LocalFolderScanner,
)

__all__ = [
    # Local folder
    "LocalFolderScanner",
    "SUPPORTED_EXTENSIONS",
    "FolderWatcher",
    "PhotoFileEventHandler",
    "get_folder_watcher",
    "setup_watcher_callbacks",
    # Google Photos
    "GooglePhotosClient",
    "GooglePhotosPickerClient",
    "PickerSession",
    "PickerMediaItem",
]
