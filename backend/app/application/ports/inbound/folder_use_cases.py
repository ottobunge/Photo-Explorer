"""Folder use cases - Inbound port for folder scanning operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class WatchedFolder:
    """Representation of a watched folder."""

    id: UUID
    path: str
    name: Optional[str]
    recursive: bool
    auto_album: bool
    last_scanned_at: Optional[datetime]
    created_at: datetime


@dataclass
class FolderStats:
    """Statistics for a watched folder."""

    total_files: int
    processed: int
    pending: int
    failed: int


class FolderUseCases(ABC):
    """Interface defining folder scanning use cases."""

    @abstractmethod
    async def register_folder(
        self,
        path: str,
        name: Optional[str] = None,
        recursive: bool = True,
        auto_album: bool = False,
    ) -> WatchedFolder:
        """
        Register a folder for scanning.

        Args:
            path: Absolute path to the folder
            name: Optional display name
            recursive: Whether to scan subdirectories
            auto_album: Whether to create albums from subfolders

        Returns:
            The created WatchedFolder
        """
        pass

    @abstractmethod
    async def list_folders(self) -> list[WatchedFolder]:
        """
        List all watched folders.

        Returns:
            List of WatchedFolder entities
        """
        pass

    @abstractmethod
    async def get_folder(self, folder_id: UUID) -> Optional[WatchedFolder]:
        """
        Get a watched folder by ID.

        Args:
            folder_id: The folder's unique identifier

        Returns:
            The WatchedFolder or None if not found
        """
        pass

    @abstractmethod
    async def get_folder_stats(self, folder_id: UUID) -> Optional[FolderStats]:
        """
        Get statistics for a watched folder.

        Args:
            folder_id: The folder's unique identifier

        Returns:
            FolderStats or None if folder not found
        """
        pass

    @abstractmethod
    async def trigger_scan(self, folder_id: UUID) -> bool:
        """
        Trigger a scan of a watched folder.

        Args:
            folder_id: The folder's unique identifier

        Returns:
            True if scan was triggered, False if folder not found
        """
        pass

    @abstractmethod
    async def remove_folder(
        self,
        folder_id: UUID,
        delete_photos: bool = False,
    ) -> bool:
        """
        Remove a watched folder.

        Args:
            folder_id: The folder's unique identifier
            delete_photos: Whether to also delete imported photos

        Returns:
            True if removed, False if not found
        """
        pass
