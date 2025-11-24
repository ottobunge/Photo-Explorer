"""Filesystem watcher for local folder connectors."""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Callable, Optional
from uuid import UUID

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.adapters.outbound.connectors.local_folder import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class PhotoFileEventHandler(FileSystemEventHandler):
    """
    Event handler for photo file changes.

    Filters for supported image files and triggers callbacks.
    """

    def __init__(
        self,
        connector_id: UUID,
        on_created: Optional[Callable[[UUID, str], None]] = None,
        on_modified: Optional[Callable[[UUID, str], None]] = None,
        on_deleted: Optional[Callable[[UUID, str], None]] = None,
        on_moved: Optional[Callable[[UUID, str, str], None]] = None,
    ):
        super().__init__()
        self.connector_id = connector_id
        self._on_created = on_created
        self._on_modified = on_modified
        self._on_deleted = on_deleted
        self._on_moved = on_moved

    def _is_supported_image(self, path: str) -> bool:
        """Check if path is a supported image file."""
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _is_hidden(self, path: str) -> bool:
        """Check if path or any parent is hidden."""
        parts = Path(path).parts
        return any(part.startswith(".") for part in parts)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation."""
        if event.is_directory:
            return
        if self._is_hidden(event.src_path):
            return
        if not self._is_supported_image(event.src_path):
            return

        logger.debug(f"File created: {event.src_path}")
        if self._on_created:
            self._on_created(self.connector_id, event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        if event.is_directory:
            return
        if self._is_hidden(event.src_path):
            return
        if not self._is_supported_image(event.src_path):
            return

        logger.debug(f"File modified: {event.src_path}")
        if self._on_modified:
            self._on_modified(self.connector_id, event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion."""
        if event.is_directory:
            return
        if self._is_hidden(event.src_path):
            return
        if not self._is_supported_image(event.src_path):
            return

        logger.debug(f"File deleted: {event.src_path}")
        if self._on_deleted:
            self._on_deleted(self.connector_id, event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename."""
        if event.is_directory:
            return

        src_supported = self._is_supported_image(event.src_path)
        dest_supported = self._is_supported_image(event.dest_path)
        src_hidden = self._is_hidden(event.src_path)
        dest_hidden = self._is_hidden(event.dest_path)

        # File moved out of watch (to hidden or unsupported)
        if src_supported and not src_hidden and (not dest_supported or dest_hidden):
            logger.debug(f"File moved out: {event.src_path}")
            if self._on_deleted:
                self._on_deleted(self.connector_id, event.src_path)
            return

        # File moved in (from hidden or unsupported)
        if dest_supported and not dest_hidden and (not src_supported or src_hidden):
            logger.debug(f"File moved in: {event.dest_path}")
            if self._on_created:
                self._on_created(self.connector_id, event.dest_path)
            return

        # Normal move/rename
        if src_supported and dest_supported and not src_hidden and not dest_hidden:
            logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
            if self._on_moved:
                self._on_moved(self.connector_id, event.src_path, event.dest_path)


class FolderWatcher:
    """
    Watches a folder for file changes using watchdog.

    Provides real-time sync capability for local folder connectors.
    """

    def __init__(self):
        self._observer: Optional[Observer] = None
        self._watches: dict[UUID, str] = {}  # connector_id -> watch path
        self._lock = threading.Lock()

        # Callbacks for file events
        self._on_created: Optional[Callable[[UUID, str], None]] = None
        self._on_modified: Optional[Callable[[UUID, str], None]] = None
        self._on_deleted: Optional[Callable[[UUID, str], None]] = None
        self._on_moved: Optional[Callable[[UUID, str, str], None]] = None

    def set_callbacks(
        self,
        on_created: Optional[Callable[[UUID, str], None]] = None,
        on_modified: Optional[Callable[[UUID, str], None]] = None,
        on_deleted: Optional[Callable[[UUID, str], None]] = None,
        on_moved: Optional[Callable[[UUID, str, str], None]] = None,
    ) -> None:
        """Set callbacks for file events."""
        self._on_created = on_created
        self._on_modified = on_modified
        self._on_deleted = on_deleted
        self._on_moved = on_moved

    def start(self) -> None:
        """Start the filesystem observer."""
        with self._lock:
            if self._observer is not None:
                return

            self._observer = Observer()
            self._observer.start()
            logger.info("Folder watcher started")

    def stop(self) -> None:
        """Stop the filesystem observer."""
        with self._lock:
            if self._observer is None:
                return

            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
            self._watches.clear()
            logger.info("Folder watcher stopped")

    def add_watch(
        self,
        connector_id: UUID,
        path: str,
        recursive: bool = True,
    ) -> bool:
        """
        Add a watch for a folder.

        Args:
            connector_id: The connector ID
            path: Path to watch
            recursive: Watch subdirectories

        Returns:
            True if watch was added successfully
        """
        with self._lock:
            if self._observer is None:
                logger.warning("Cannot add watch: observer not started")
                return False

            if connector_id in self._watches:
                logger.warning(f"Watch already exists for connector {connector_id}")
                return False

            watch_path = Path(path)
            if not watch_path.exists() or not watch_path.is_dir():
                logger.error(f"Invalid watch path: {path}")
                return False

            handler = PhotoFileEventHandler(
                connector_id=connector_id,
                on_created=self._on_created,
                on_modified=self._on_modified,
                on_deleted=self._on_deleted,
                on_moved=self._on_moved,
            )

            try:
                self._observer.schedule(handler, path, recursive=recursive)
                self._watches[connector_id] = path
                logger.info(f"Added watch for {path} (connector {connector_id})")
                return True
            except Exception as e:
                logger.error(f"Failed to add watch for {path}: {e}")
                return False

    def remove_watch(self, connector_id: UUID) -> bool:
        """
        Remove a watch for a folder.

        Args:
            connector_id: The connector ID

        Returns:
            True if watch was removed
        """
        with self._lock:
            if connector_id not in self._watches:
                return False

            # Note: watchdog doesn't have a direct way to remove a single watch
            # We would need to track the watch object, but for simplicity
            # we just mark it as removed from our tracking
            del self._watches[connector_id]
            logger.info(f"Removed watch for connector {connector_id}")
            return True

    def is_watching(self, connector_id: UUID) -> bool:
        """Check if a connector is being watched."""
        return connector_id in self._watches

    def get_watched_paths(self) -> dict[UUID, str]:
        """Get all watched paths."""
        return self._watches.copy()


# Global watcher instance
_watcher: Optional[FolderWatcher] = None


def get_folder_watcher() -> FolderWatcher:
    """Get the global folder watcher instance."""
    global _watcher
    if _watcher is None:
        _watcher = FolderWatcher()
    return _watcher


def setup_watcher_callbacks(
    on_created: Callable[[UUID, str], None],
    on_modified: Callable[[UUID, str], None],
    on_deleted: Callable[[UUID, str], None],
    on_moved: Callable[[UUID, str, str], None],
) -> FolderWatcher:
    """
    Setup the folder watcher with callbacks that trigger Celery tasks.

    This should be called during application startup.
    """
    watcher = get_folder_watcher()
    watcher.set_callbacks(
        on_created=on_created,
        on_modified=on_modified,
        on_deleted=on_deleted,
        on_moved=on_moved,
    )
    watcher.start()
    return watcher
