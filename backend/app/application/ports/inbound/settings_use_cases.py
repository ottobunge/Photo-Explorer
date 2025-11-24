"""Settings use cases - Inbound port for application settings."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AppSettings:
    """Application settings."""

    # Storage paths
    config_dir: Path
    data_dir: Path
    cache_dir: Path

    # Indexing settings
    thumbnail_cache_hours: int = 24
    indexing_batch_size: int = 100
    indexing_parallel_workers: int = 4

    # Sync settings
    default_sync_interval_hours: int = 6


@dataclass
class ConnectorSettings:
    """Settings for a specific connector."""

    connector_type: str
    enabled: bool
    config: dict


class SettingsUseCases(ABC):
    """Interface for settings management."""

    @abstractmethod
    async def get_settings(self) -> AppSettings:
        """
        Get the current application settings.

        Returns:
            AppSettings object
        """
        pass

    @abstractmethod
    async def update_settings(
        self,
        thumbnail_cache_hours: Optional[int] = None,
        indexing_batch_size: Optional[int] = None,
        indexing_parallel_workers: Optional[int] = None,
        default_sync_interval_hours: Optional[int] = None,
    ) -> AppSettings:
        """
        Update application settings.

        Returns:
            Updated AppSettings object
        """
        pass

    @abstractmethod
    async def get_connector_settings(self, connector_type: str) -> Optional[ConnectorSettings]:
        """
        Get settings for a specific connector.

        Args:
            connector_type: The connector type (e.g., "google_photos")

        Returns:
            ConnectorSettings or None if not found
        """
        pass

    @abstractmethod
    async def save_connector_settings(
        self,
        connector_type: str,
        config: dict,
    ) -> ConnectorSettings:
        """
        Save settings for a specific connector.

        Args:
            connector_type: The connector type
            config: The configuration to save

        Returns:
            Saved ConnectorSettings
        """
        pass

    @abstractmethod
    async def get_storage_stats(self) -> dict:
        """
        Get storage usage statistics.

        Returns:
            Dictionary with storage stats (photos, thumbnails, cache, etc.)
        """
        pass
