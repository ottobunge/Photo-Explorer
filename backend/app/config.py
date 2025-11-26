"""Application configuration using pydantic-settings."""

import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are validated at startup. Missing required variables or
    invalid formats will cause the application to fail fast with clear errors.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(
        default="Photo Explorer",
        description="Application name displayed in API docs",
        min_length=1,
        max_length=100,
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (verbose logging, detailed errors)",
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload on code changes (development only)",
    )

    # Database - no default credentials; must be set via environment
    database_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/photo_explorer",
        description="PostgreSQL database connection URL with asyncpg driver",
        min_length=1,
    )
    db_pool_size: int = Field(
        default=5,
        description="Database connection pool size",
        gt=0,
        le=100,
    )
    db_max_overflow: int = Field(
        default=10,
        description="Maximum number of connections that can be created beyond pool_size",
        ge=0,
        le=100,
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Timeout in seconds for getting a connection from the pool",
        gt=0,
        le=300,
    )

    # Vector database
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL",
        pattern=r"^https?://",
    )
    qdrant_collection_photos: str = Field(
        default="photo_embeddings",
        description="Qdrant collection name for photo embeddings",
        min_length=1,
        max_length=100,
    )
    qdrant_collection_faces: str = Field(
        default="face_embeddings",
        description="Qdrant collection name for face embeddings",
        min_length=1,
        max_length=100,
    )

    # Redis/Celery
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for Celery broker and cache",
        pattern=r"^redis://",
    )

    # Security
    token_encryption_key: str = Field(
        ...,  # Required field, no default
        description="32-byte encryption key for OAuth tokens (base64 encoded)",
        min_length=32,
    )
    allowed_local_connector_paths: list[str] = Field(
        default_factory=lambda: [str(Path.home())],
        description="Allowed base paths for local folder connectors (prevents system directory access)",
    )

    @field_validator("allowed_local_connector_paths")
    @classmethod
    def validate_allowed_paths(cls, v: list[str]) -> list[str]:
        """Validate allowed paths are absolute and normalized.

        Args:
            v: List of allowed base paths

        Returns:
            List of absolute, normalized paths

        Raises:
            ValueError: If any path is invalid
        """
        if not v:
            msg = "At least one allowed path must be configured"
            raise ValueError(msg)

        normalized = []
        for path_str in v:
            path = Path(path_str).resolve()

            # Block system directories
            system_dirs = {"/etc", "/var", "/sys", "/proc", "/dev", "/boot", "/root"}
            if str(path) in system_dirs or any(str(path).startswith(d + "/") for d in system_dirs):
                msg = f"System directory not allowed: {path}"
                raise ValueError(msg)

            normalized.append(str(path))

        return normalized

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format and driver.

        Args:
            v: Database URL string

        Returns:
            Validated database URL

        Raises:
            ValueError: If URL is invalid or missing asyncpg driver
        """
        if not v:
            msg = "database_url cannot be empty"
            raise ValueError(msg)

        if "postgresql" not in v.lower():
            msg = "database_url must be a PostgreSQL connection string"
            raise ValueError(msg)

        if "asyncpg" not in v:
            msg = "database_url must use asyncpg driver (postgresql+asyncpg://...)"
            raise ValueError(msg)

        return v

    @field_validator("token_encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate encryption key is sufficiently long.

        Args:
            v: Encryption key string

        Returns:
            Validated encryption key

        Raises:
            ValueError: If key is too short or invalid
        """
        if not v:
            msg = (
                "token_encryption_key is required. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())'"
            )
            raise ValueError(msg)

        if len(v) < 32:
            msg = (
                f"token_encryption_key must be at least 32 bytes, got {len(v)}. "
                "Use Fernet.generate_key() to generate a secure key."
            )
            raise ValueError(msg)

        return v

    @field_validator("qdrant_url")
    @classmethod
    def validate_qdrant_url(cls, v: str) -> str:
        """Validate Qdrant URL format.

        Args:
            v: Qdrant URL string

        Returns:
            Validated URL

        Raises:
            ValueError: If URL format is invalid
        """
        if not v.startswith(("http://", "https://")):
            msg = "qdrant_url must start with http:// or https://"
            raise ValueError(msg)

        return v.rstrip("/")  # Remove trailing slash

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format.

        Args:
            v: Redis URL string

        Returns:
            Validated URL

        Raises:
            ValueError: If URL format is invalid
        """
        if not v.startswith("redis://"):
            msg = "redis_url must start with redis://"
            raise ValueError(msg)

        return v

    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL derived from redis_url."""
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        """Celery result backend URL (uses db 1 for separation)."""
        # Replace /0 with /1 for result backend
        if self.redis_url.endswith("/0"):
            return self.redis_url[:-1] + "1"
        return self.redis_url

    # Storage
    storage_path: Path = Field(
        default=Path("./storage"),
        description="Base directory for file storage",
    )
    thumbnails_path: Path = Field(
        default=Path("./storage/thumbnails"),
        description="Directory for thumbnail images",
    )
    faces_path: Path = Field(
        default=Path("./storage/faces"),
        description="Directory for extracted face crops",
    )

    # ML Models
    models_path: Path = Field(
        default=Path("./models"),
        description="Directory for downloaded ML models",
    )
    clip_model_name: str = Field(
        default="ViT-L-14",
        description="CLIP model architecture name",
        min_length=1,
    )
    clip_pretrained: str = Field(
        default="openai",
        description="CLIP pretrained weights source",
        min_length=1,
    )

    # Processing
    thumbnail_size: tuple[int, int] = Field(
        default=(400, 400),
        description="Thumbnail dimensions (width, height) in pixels",
    )
    face_crop_size: tuple[int, int] = Field(
        default=(160, 160),
        description="Face crop dimensions (width, height) in pixels",
    )
    max_upload_size_mb: int = Field(
        default=50,
        description="Maximum file upload size in megabytes",
        gt=0,
        le=1000,
    )

    # API
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API version prefix for all routes",
        pattern=r"^/api/v\d+$",
    )

    @field_validator("thumbnail_size", "face_crop_size")
    @classmethod
    def validate_image_size(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Validate image dimensions are positive and reasonable.

        Args:
            v: Image dimensions tuple (width, height)

        Returns:
            Validated dimensions

        Raises:
            ValueError: If dimensions are invalid
        """
        width, height = v
        if width <= 0 or height <= 0:
            msg = f"Image dimensions must be positive, got {v}"
            raise ValueError(msg)

        if width > 4096 or height > 4096:
            msg = f"Image dimensions too large (max 4096), got {v}"
            raise ValueError(msg)

        return v

    @field_validator("storage_path", "thumbnails_path", "faces_path", "models_path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Validate and normalize paths.

        Args:
            v: Path to validate

        Returns:
            Absolute, normalized path

        Raises:
            ValueError: If path is invalid
        """
        if not v:
            msg = "Path cannot be empty"
            raise ValueError(msg)

        # Convert to absolute path
        return v.resolve()

    @property
    def storage_photos_path(self) -> Path:
        """Path for storing original photos."""
        return self.storage_path / "photos"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        for path in [
            self.storage_path,
            self.storage_photos_path,
            self.thumbnails_path,
            self.faces_path,
            self.models_path,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def is_path_allowed(self, requested_path: str | Path) -> tuple[bool, str | None]:
        """Check if a path is within allowed base directories.

        This prevents path traversal attacks by ensuring local connector
        paths are restricted to configured safe directories.

        Args:
            requested_path: Path to validate

        Returns:
            Tuple of (is_allowed, error_message). error_message is None if allowed.

        Examples:
            >>> settings = Settings()
            >>> settings.is_path_allowed("/home/user/photos")
            (True, None)
            >>> settings.is_path_allowed("/etc/passwd")
            (False, "Path /etc/passwd is not within allowed directories")
        """
        try:
            # Resolve to absolute path and follow symlinks
            path = Path(requested_path).resolve()
        except (OSError, RuntimeError) as e:
            return False, f"Invalid path: {e}"

        # Check if path is within any allowed base directory
        for allowed_base in self.allowed_local_connector_paths:
            allowed = Path(allowed_base).resolve()
            try:
                # Use relative_to to check if path is under allowed base
                # This will raise ValueError if not a subdirectory
                path.relative_to(allowed)
                return True, None
            except ValueError:
                continue

        # Not within any allowed directory
        allowed_str = ", ".join(self.allowed_local_connector_paths)
        return False, f"Path {path} is not within allowed directories: {allowed_str}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Loads and validates settings from environment variables.
    On validation failure, logs clear error message and exits.

    Returns:
        Validated Settings instance

    Raises:
        SystemExit: If settings validation fails
    """
    try:
        settings = Settings()
        settings.ensure_directories()
        return settings
    except Exception as exc:
        # Log validation error with clear message
        import logging

        logger = logging.getLogger(__name__)
        logger.critical(
            "Configuration validation failed. Please check your environment variables.",
            exc_info=True,
        )
        # Print to stderr for visibility
        print(
            f"\nFATAL ERROR: Configuration validation failed:\n{exc}\n\n"
            "Please check your .env file and ensure all required variables are set correctly.\n"
            "See .env.example for reference.\n",
            file=sys.stderr,
        )
        sys.exit(1)
