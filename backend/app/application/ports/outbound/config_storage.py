"""Config storage port - Interface for configuration file storage."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class ConfigStorage(ABC):
    """Interface for configuration file storage."""

    @abstractmethod
    async def load_config(self, name: str) -> Optional[dict[str, Any]]:
        """
        Load a configuration file.

        Args:
            name: The config name (e.g., "config", "google-photos")

        Returns:
            The configuration as a dictionary or None if not found
        """
        pass

    @abstractmethod
    async def save_config(self, name: str, config: dict[str, Any]) -> None:
        """
        Save a configuration file.

        Args:
            name: The config name
            config: The configuration to save
        """
        pass

    @abstractmethod
    async def delete_config(self, name: str) -> bool:
        """
        Delete a configuration file.

        Args:
            name: The config name

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def get_config_path(self, name: str) -> Path:
        """
        Get the path for a configuration file.

        Args:
            name: The config name

        Returns:
            The Path to the configuration file
        """
        pass

    @abstractmethod
    def get_config_dir(self) -> Path:
        """
        Get the base configuration directory.

        Returns:
            The Path to the configuration directory
        """
        pass
