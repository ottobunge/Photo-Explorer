"""Token storage port - Interface for secure OAuth token storage."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OAuthTokens:
    """OAuth token data."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime
    scopes: list[str]

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        return datetime.now(timezone.utc) >= self.expires_at


class TokenStorage(ABC):
    """Interface for secure OAuth token storage."""

    @abstractmethod
    async def save_tokens(self, connector_type: str, tokens: OAuthTokens) -> None:
        """
        Save OAuth tokens for a connector.

        Tokens should be encrypted at rest.

        Args:
            connector_type: The connector type (e.g., "google_photos")
            tokens: The OAuth tokens to save
        """

    @abstractmethod
    async def load_tokens(self, connector_type: str) -> Optional[OAuthTokens]:
        """
        Load OAuth tokens for a connector.

        Args:
            connector_type: The connector type

        Returns:
            The OAuthTokens or None if not found
        """

    @abstractmethod
    async def delete_tokens(self, connector_type: str) -> bool:
        """
        Delete OAuth tokens for a connector.

        Args:
            connector_type: The connector type

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def has_tokens(self, connector_type: str) -> bool:
        """
        Check if tokens exist for a connector.

        Args:
            connector_type: The connector type

        Returns:
            True if tokens exist
        """
