"""Secure OAuth token storage with encryption at rest."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles
import aiofiles.os
from cryptography.fernet import Fernet

from app.application.ports.outbound import OAuthTokens, TokenStorage

logger = logging.getLogger(__name__)


class SecureTokenStorage(TokenStorage):
    """
    Secure token storage implementation using Fernet encryption.

    Stores OAuth tokens encrypted at rest in JSON files.
    The encryption key should be provided via environment variable
    or generated and stored securely.
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize secure token storage.

        Args:
            storage_dir: Directory to store encrypted tokens.
                        Defaults to DATA_DIR/tokens or ~/.photo-explorer/tokens
            encryption_key: Fernet encryption key (base64 encoded).
                           Defaults to TOKEN_ENCRYPTION_KEY env var.
                           If not found, generates and stores a new key.
        """
        # Determine storage directory
        if storage_dir:
            self._storage_dir = Path(storage_dir)
        else:
            data_dir = os.environ.get("DATA_DIR", "")
            if data_dir:
                self._storage_dir = Path(data_dir) / "tokens"
            else:
                self._storage_dir = Path.home() / ".photo-explorer" / "tokens"

        # Get or generate encryption key
        self._encryption_key = encryption_key or os.environ.get("TOKEN_ENCRYPTION_KEY")
        self._fernet: Optional[Fernet] = None
        self._lock = asyncio.Lock()

    async def _ensure_setup(self) -> None:
        """Ensure storage directory exists and encryption is initialized."""
        async with self._lock:
            # Create storage directory
            if not self._storage_dir.exists():
                self._storage_dir.mkdir(parents=True, mode=0o700)

            # Initialize Fernet encryption
            if self._fernet is None:
                if self._encryption_key:
                    self._fernet = Fernet(self._encryption_key.encode())
                else:
                    # Generate new key and store it
                    key = Fernet.generate_key()
                    self._fernet = Fernet(key)
                    await self._save_key(key)
                    logger.warning(
                        "Generated new token encryption key. "
                        "For production, set TOKEN_ENCRYPTION_KEY environment variable."
                    )

    async def _save_key(self, key: bytes) -> None:
        """Save the encryption key to a secure file."""
        key_file = self._storage_dir / ".encryption_key"
        async with aiofiles.open(key_file, "wb") as f:
            await f.write(key)
        # Set restrictive permissions
        os.chmod(key_file, 0o600)

    async def _load_stored_key(self) -> Optional[bytes]:
        """Load a previously stored encryption key."""
        key_file = self._storage_dir / ".encryption_key"
        if key_file.exists():
            async with aiofiles.open(key_file, "rb") as f:
                return await f.read()
        return None

    def _get_token_path(self, connector_type: str) -> Path:
        """Get the file path for a connector's tokens."""
        # Sanitize connector type for use as filename
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in connector_type)
        return self._storage_dir / f"{safe_name}.tokens"

    async def save_tokens(self, connector_type: str, tokens: OAuthTokens) -> None:
        """
        Save OAuth tokens for a connector.

        Tokens are encrypted using Fernet before being stored.

        Args:
            connector_type: The connector type (e.g., "google_photos")
            tokens: The OAuth tokens to save
        """
        await self._ensure_setup()

        # Serialize tokens to JSON
        token_data = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "expires_at": tokens.expires_at.isoformat(),
            "scopes": tokens.scopes,
        }
        json_data = json.dumps(token_data)

        # Encrypt the data
        encrypted = self._fernet.encrypt(json_data.encode())

        # Write to file
        token_path = self._get_token_path(connector_type)
        async with aiofiles.open(token_path, "wb") as f:
            await f.write(encrypted)

        # Set restrictive permissions
        os.chmod(token_path, 0o600)

        logger.debug(f"Saved tokens for connector: {connector_type}")

    async def load_tokens(self, connector_type: str) -> Optional[OAuthTokens]:
        """
        Load OAuth tokens for a connector.

        Args:
            connector_type: The connector type

        Returns:
            The OAuthTokens or None if not found
        """
        await self._ensure_setup()

        token_path = self._get_token_path(connector_type)
        if not token_path.exists():
            return None

        try:
            # Read encrypted data
            async with aiofiles.open(token_path, "rb") as f:
                encrypted = await f.read()

            # Decrypt
            json_data = self._fernet.decrypt(encrypted).decode()
            token_data = json.loads(json_data)

            # Parse tokens
            return OAuthTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_type=token_data["token_type"],
                expires_at=datetime.fromisoformat(token_data["expires_at"]),
                scopes=token_data["scopes"],
            )

        except Exception as e:
            logger.error(f"Failed to load tokens for {connector_type}: {e}")
            return None

    async def delete_tokens(self, connector_type: str) -> bool:
        """
        Delete OAuth tokens for a connector.

        Args:
            connector_type: The connector type

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_setup()

        token_path = self._get_token_path(connector_type)
        if not token_path.exists():
            return False

        try:
            await aiofiles.os.remove(token_path)
            logger.debug(f"Deleted tokens for connector: {connector_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete tokens for {connector_type}: {e}")
            return False

    async def has_tokens(self, connector_type: str) -> bool:
        """
        Check if tokens exist for a connector.

        Args:
            connector_type: The connector type

        Returns:
            True if tokens exist
        """
        token_path = self._get_token_path(connector_type)
        return token_path.exists()


class DatabaseTokenStorage(TokenStorage):
    """
    Token storage implementation using the database.

    Stores encrypted tokens in the PostgreSQL database.
    This is an alternative to file-based storage for distributed deployments.
    """

    def __init__(
        self,
        session_factory,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize database token storage.

        Args:
            session_factory: SQLAlchemy async session factory
            encryption_key: Fernet encryption key (base64 encoded)
        """
        self._session_factory = session_factory
        self._encryption_key = encryption_key or os.environ.get("TOKEN_ENCRYPTION_KEY")

        if not self._encryption_key:
            raise ValueError(
                "TOKEN_ENCRYPTION_KEY environment variable is required "
                "for database token storage"
            )

        self._fernet = Fernet(self._encryption_key.encode())

    async def save_tokens(self, connector_type: str, tokens: OAuthTokens) -> None:
        """Save OAuth tokens for a connector."""
        from app.adapters.outbound.persistence.postgres.models import OAuthTokenModel

        # Serialize and encrypt
        token_data = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "expires_at": tokens.expires_at.isoformat(),
            "scopes": tokens.scopes,
        }
        encrypted = self._fernet.encrypt(json.dumps(token_data).encode()).decode()

        async with self._session_factory() as session:
            from sqlalchemy import select

            # Check if exists
            stmt = select(OAuthTokenModel).where(
                OAuthTokenModel.connector_type == connector_type
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.encrypted_data = encrypted
                existing.updated_at = datetime.now(timezone.utc)
            else:
                token_model = OAuthTokenModel(
                    connector_type=connector_type,
                    encrypted_data=encrypted,
                )
                session.add(token_model)

            await session.commit()

    async def load_tokens(self, connector_type: str) -> Optional[OAuthTokens]:
        """Load OAuth tokens for a connector."""
        from app.adapters.outbound.persistence.postgres.models import OAuthTokenModel

        async with self._session_factory() as session:
            from sqlalchemy import select

            stmt = select(OAuthTokenModel).where(
                OAuthTokenModel.connector_type == connector_type
            )
            result = await session.execute(stmt)
            token_model = result.scalar_one_or_none()

            if not token_model:
                return None

            try:
                json_data = self._fernet.decrypt(
                    token_model.encrypted_data.encode()
                ).decode()
                token_data = json.loads(json_data)

                return OAuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    token_type=token_data["token_type"],
                    expires_at=datetime.fromisoformat(token_data["expires_at"]),
                    scopes=token_data["scopes"],
                )
            except Exception as e:
                logger.error(f"Failed to decrypt tokens: {e}")
                return None

    async def delete_tokens(self, connector_type: str) -> bool:
        """Delete OAuth tokens for a connector."""
        from app.adapters.outbound.persistence.postgres.models import OAuthTokenModel

        async with self._session_factory() as session:
            from sqlalchemy import delete

            stmt = delete(OAuthTokenModel).where(
                OAuthTokenModel.connector_type == connector_type
            )
            result = await session.execute(stmt)
            await session.commit()

            return result.rowcount > 0

    async def has_tokens(self, connector_type: str) -> bool:
        """Check if tokens exist for a connector."""
        from app.adapters.outbound.persistence.postgres.models import OAuthTokenModel

        async with self._session_factory() as session:
            from sqlalchemy import select, func

            stmt = select(func.count()).select_from(OAuthTokenModel).where(
                OAuthTokenModel.connector_type == connector_type
            )
            result = await session.execute(stmt)
            count = result.scalar()

            return count > 0
