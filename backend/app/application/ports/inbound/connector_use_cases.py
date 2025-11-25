"""Connector use cases - Inbound port for connector operations."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import Connector, SyncStats


class ConnectorUseCases(ABC):
    """Interface defining connector-related use cases."""

    @abstractmethod
    async def list_connectors(self) -> list[Connector]:
        """
        List all configured connectors.

        Returns:
            List of Connector entities
        """

    @abstractmethod
    async def get_connector(self, connector_id: UUID) -> Optional[Connector]:
        """
        Get a connector by ID.

        Args:
            connector_id: The connector's unique identifier

        Returns:
            The Connector entity or None if not found
        """

    @abstractmethod
    async def get_connector_by_type(self, connector_type: str) -> Optional[Connector]:
        """
        Get a connector by type (e.g., "google_photos").

        Args:
            connector_type: The connector type

        Returns:
            The Connector entity or None if not found
        """

    @abstractmethod
    async def create_local_connector(
        self,
        path: str,
        name: Optional[str] = None,
        recursive: bool = True,
        watch: bool = True,
        auto_album: bool = False,
    ) -> Connector:
        """
        Create a local folder connector.

        Args:
            path: Absolute path to the folder
            name: Optional display name
            recursive: Whether to scan subdirectories
            watch: Whether to watch for filesystem changes
            auto_album: Whether to create albums from subfolders

        Returns:
            The created Connector entity
        """

    @abstractmethod
    async def update_connector(
        self,
        connector_id: UUID,
        config: Optional[dict] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[Connector]:
        """
        Update a connector's configuration.

        Args:
            connector_id: The connector's unique identifier
            config: Configuration updates
            enabled: Whether the connector is enabled

        Returns:
            The updated Connector entity or None if not found
        """

    @abstractmethod
    async def delete_connector(
        self,
        connector_id: UUID,
        delete_photos: bool = False,
    ) -> bool:
        """
        Delete a connector.

        Args:
            connector_id: The connector's unique identifier
            delete_photos: Whether to also delete indexed photos

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def trigger_sync(self, connector_id: UUID) -> bool:
        """
        Trigger a manual sync for a connector.

        Args:
            connector_id: The connector's unique identifier

        Returns:
            True if sync was triggered, False if connector not found
        """

    @abstractmethod
    async def get_sync_status(self, connector_id: UUID) -> Optional[SyncStats]:
        """
        Get the current sync status for a connector.

        Args:
            connector_id: The connector's unique identifier

        Returns:
            SyncStats or None if not syncing/not found
        """


class GooglePhotosConnectorUseCases(ABC):
    """Interface for Google Photos specific operations."""

    @abstractmethod
    async def get_auth_url(self, redirect_uri: str) -> str:
        """
        Get the OAuth authorization URL for Google Photos.

        Args:
            redirect_uri: The callback URL for OAuth

        Returns:
            The authorization URL to redirect the user to
        """

    @abstractmethod
    async def handle_oauth_callback(
        self,
        code: str,
        redirect_uri: str,
    ) -> Connector:
        """
        Handle the OAuth callback from Google.

        Args:
            code: The authorization code from Google
            redirect_uri: The callback URL used

        Returns:
            The connected Connector entity
        """

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from Google Photos and revoke tokens.

        Returns:
            True if disconnected successfully
        """

    @abstractmethod
    async def get_connection_status(self) -> dict:
        """
        Get the current Google Photos connection status.

        Returns:
            Dictionary with connection status details
        """

    @abstractmethod
    async def get_photo_url(
        self,
        external_id: str,
        width: int = 2048,
        height: int = 2048,
    ) -> Optional[str]:
        """
        Get a fresh URL for viewing a Google Photos image.

        Args:
            external_id: The media item ID in Google Photos
            width: Desired width
            height: Desired height

        Returns:
            The image URL or None if not found
        """
