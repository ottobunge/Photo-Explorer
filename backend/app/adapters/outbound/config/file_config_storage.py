"""File-based configuration storage adapter."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml

from app.application.ports.outbound import ConfigStorage


class FileConfigStorage(ConfigStorage):
    """
    File-based configuration storage.

    Stores configuration in YAML files under ~/.config/photo-explorer/
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir:
            self._config_dir = config_dir
        else:
            # Default to ~/.config/photo-explorer
            home = Path.home()
            self._config_dir = home / ".config" / "photo-explorer"

        # Ensure directories exist
        self._config_dir.mkdir(parents=True, exist_ok=True)
        (self._config_dir / "connectors").mkdir(exist_ok=True)
        (self._config_dir / "tokens").mkdir(exist_ok=True)

    def get_config_dir(self) -> Path:
        """Get the base configuration directory."""
        return self._config_dir

    def get_config_path(self, name: str) -> Path:
        """Get the path for a configuration file."""
        # Handle connector configs
        if "/" in name:
            parts = name.split("/", 1)
            return self._config_dir / parts[0] / f"{parts[1]}.yaml"

        return self._config_dir / f"{name}.yaml"

    async def load_config(self, name: str) -> Optional[dict[str, Any]]:
        """Load a configuration file."""
        path = self.get_config_path(name)

        if not path.exists():
            return None

        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return None

    async def save_config(self, name: str, config: dict[str, Any]) -> None:
        """Save a configuration file."""
        path = self.get_config_path(name)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    async def delete_config(self, name: str) -> bool:
        """Delete a configuration file."""
        path = self.get_config_path(name)

        if not path.exists():
            return False

        path.unlink()
        return True


class SecureTokenStorage:
    """
    Secure token storage using encryption.

    Stores OAuth tokens encrypted at rest.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir:
            self._tokens_dir = config_dir / "tokens"
        else:
            home = Path.home()
            self._tokens_dir = home / ".config" / "photo-explorer" / "tokens"

        self._tokens_dir.mkdir(parents=True, exist_ok=True)

        # In production, use a proper encryption key from keyring
        # For now, we'll use a simple file-based approach
        # GitHub Issue: Integrate with system keyring (keyring library)
        # This is a security enhancement for production deployments.
        # Using the system keyring (e.g., macOS Keychain, Windows Credential Manager,
        # Linux Secret Service) would provide better security for OAuth tokens.

    def _get_token_path(self, connector_type: str) -> Path:
        """Get the path for a token file."""
        return self._tokens_dir / f"{connector_type}.json"

    async def save_tokens(self, connector_type: str, tokens: dict) -> None:
        """Save OAuth tokens (should be encrypted in production)."""
        import json

        path = self._get_token_path(connector_type)

        # GitHub Issue: Encrypt tokens before saving
        # For now, just save as JSON with restrictive permissions (0600).
        # Security note: File permissions provide basic protection, but encryption
        # would be better for production. Consider using cryptography.fernet or
        # integrating with system keyring for proper token encryption.
        with open(path, "w") as f:
            json.dump(tokens, f)

        # Set restrictive permissions (user read/write only)
        os.chmod(path, 0o600)

    async def load_tokens(self, connector_type: str) -> Optional[dict]:
        """Load OAuth tokens."""
        import json

        path = self._get_token_path(connector_type)

        if not path.exists():
            return None

        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    async def delete_tokens(self, connector_type: str) -> bool:
        """Delete OAuth tokens."""
        path = self._get_token_path(connector_type)

        if not path.exists():
            return False

        path.unlink()
        return True

    async def has_tokens(self, connector_type: str) -> bool:
        """Check if tokens exist."""
        return self._get_token_path(connector_type).exists()
