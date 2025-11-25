"""Connector repository port - Interface for connector persistence."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import Connector


class ConnectorRepository(ABC):
    """Interface for connector persistence operations."""

    @abstractmethod
    async def save(self, connector: Connector) -> Connector:
        """
        Persist a connector entity.

        Args:
            connector: The connector to save

        Returns:
            The saved connector
        """
        pass

    @abstractmethod
    async def find_by_id(self, connector_id: UUID) -> Optional[Connector]:
        """
        Find a connector by its ID.

        Args:
            connector_id: The connector's unique identifier

        Returns:
            The Connector entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_type(self, connector_type: str) -> Optional[Connector]:
        """
        Find a connector by its type.

        Args:
            connector_type: The connector type (e.g., "google_photos")

        Returns:
            The Connector entity or None if not found
        """
        pass

    @abstractmethod
    async def find_all(self) -> list[Connector]:
        """
        Find all connectors.

        Returns:
            List of Connector entities
        """
        pass

    @abstractmethod
    async def find_enabled(self) -> list[Connector]:
        """
        Find all enabled connectors.

        Returns:
            List of enabled Connector entities
        """
        pass

    @abstractmethod
    async def find_by_path(self, path: str) -> Optional[Connector]:
        """
        Find a local connector by its filesystem path.

        Args:
            path: The filesystem path configured for the connector

        Returns:
            The Connector entity or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, connector_id: UUID) -> bool:
        """
        Delete a connector.

        Args:
            connector_id: The connector's unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass
