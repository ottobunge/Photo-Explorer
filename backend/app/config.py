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
