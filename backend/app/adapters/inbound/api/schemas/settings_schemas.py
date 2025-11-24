"""Settings API schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class AppSettingsData(BaseModel):
    """Application settings data."""

    # Directory paths (read-only)
    config_dir: str
    data_dir: str
    cache_dir: str

    # Indexing settings
    thumbnail_quality: int = 85
    clip_model: str = "ViT-B/32"
    face_detection_enabled: bool = True
    auto_index_new_photos: bool = True

    # Performance settings
    thumbnail_cache_hours: int = 24
    indexing_batch_size: int = 100
    indexing_parallel_workers: int = 4
    default_sync_interval_hours: int = 6


class AppSettingsResponse(BaseModel):
    """Response for application settings."""

    success: bool
    data: AppSettingsData
    error: Optional[dict[str, Any]] = None


class AppSettingsUpdate(BaseModel):
    """Request to update application settings."""

    # Indexing settings
    thumbnail_quality: Optional[int] = Field(None, ge=1, le=100, description="JPEG quality for thumbnails (1-100)")
    clip_model: Optional[str] = Field(None, min_length=1, max_length=100, description="CLIP model name")
    face_detection_enabled: Optional[bool] = Field(None, description="Enable face detection")
    auto_index_new_photos: Optional[bool] = Field(None, description="Automatically index new photos")

    # Performance settings
    thumbnail_cache_hours: Optional[int] = Field(None, ge=1, le=8760, description="Thumbnail cache duration in hours (1-8760)")
    indexing_batch_size: Optional[int] = Field(None, ge=1, le=1000, description="Batch size for indexing (1-1000)")
    indexing_parallel_workers: Optional[int] = Field(None, ge=1, le=32, description="Number of parallel workers (1-32)")
    default_sync_interval_hours: Optional[int] = Field(None, ge=1, le=168, description="Default sync interval in hours (1-168)")

    @field_validator("clip_model")
    @classmethod
    def validate_clip_model(cls, v: Optional[str]) -> Optional[str]:
        """Validate CLIP model name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("CLIP model name cannot be empty")
            # List of known valid CLIP models
            valid_models = {
                "ViT-B/32", "ViT-B/16", "ViT-L/14", "ViT-L/14@336px",
                "RN50", "RN101", "RN50x4", "RN50x16", "RN50x64"
            }
            if v not in valid_models:
                raise ValueError(f"Invalid CLIP model. Allowed: {', '.join(sorted(valid_models))}")
            return v
        return None


class StorageStatsData(BaseModel):
    """Storage statistics data."""

    total_photos: int
    local_photos: int
    remote_photos: int
    storage_used_bytes: int
    thumbnails_cached: int
    cache_size_bytes: int


class StorageStatsResponse(BaseModel):
    """Response for storage statistics."""

    success: bool
    data: StorageStatsData
    error: Optional[dict[str, Any]] = None
