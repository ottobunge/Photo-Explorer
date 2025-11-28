"""Config storage port - Interface for configuration file storage."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

# Config values can be of various types (strings, numbers, booleans, nested dicts/lists)
# We use Any here because configs are inherently flexible and extensible across different
# connector types and use cases. This is a port definition, not domain logic.
ConfigDict = dict[str, Any]  # type: ignore[explicit-any]


class ConfigStorage(ABC):
    """Interface for configuration file storage."""

    @abstractmethod
    async def load_config(self, name: str) -> Optional[ConfigDict]:
        """
        Load a configuration file.

        Args:
            name: The config name (e.g., "config", "google-photos")

        Returns:
            The configuration as a dictionary or None if not found
        """

    @abstractmethod
    async def save_config(self, name: str, config: ConfigDict) -> None:
        """
        Save a configuration file.

        Args:
            name: The config name
            config: The configuration to save
        """

    @abstractmethod
    async def delete_config(self, name: str) -> bool:
        """
        Delete a configuration file.

        Args:
            name: The config name

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    def get_config_path(self, name: str) -> Path:
        """
        Get the path for a configuration file.

        Args:
            name: The config name

        Returns:
            The Path to the configuration file
        """

    @abstractmethod
    def get_config_dir(self) -> Path:
        """
        Get the base configuration directory.

        Returns:
            The Path to the configuration directory
        """
