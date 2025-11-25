"""Settings API routes."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from app.adapters.inbound.api.schemas.settings_schemas import (
    AppSettingsResponse,
    AppSettingsUpdate,
    StorageStatsResponse,
)

router = APIRouter()


@router.get("", response_model=AppSettingsResponse)
async def get_settings() -> AppSettingsResponse:
    """Get current application settings.

    NOTE: This is a placeholder endpoint returning hardcoded values.
    GitHub Issue: Implement SettingsUseCases for persistent configuration management.
    For now, settings are managed through environment variables and config files.
    """
    # GitHub Issue: Inject SettingsUseCases for real configuration management
    return AppSettingsResponse(
        success=True,
        data={
            "config_dir": "~/.config/photo-explorer",
            "data_dir": "~/.local/share/photo-explorer",
            "cache_dir": "~/.cache/photo-explorer",
            "thumbnail_quality": 85,
            "clip_model": "ViT-B/32",
            "face_detection_enabled": True,
            "auto_index_new_photos": True,
            "thumbnail_cache_hours": 24,
            "indexing_batch_size": 100,
            "indexing_parallel_workers": 4,
            "default_sync_interval_hours": 6,
        },
    )


@router.patch("", response_model=AppSettingsResponse)
async def update_settings(request: AppSettingsUpdate) -> AppSettingsResponse:
    """Update application settings.

    NOTE: This is a placeholder endpoint that doesn't persist changes.
    GitHub Issue: Implement SettingsUseCases for persistent configuration.
    """
    # GitHub Issue: Inject SettingsUseCases for real configuration management
    return AppSettingsResponse(
        success=True,
        data={
            "config_dir": "~/.config/photo-explorer",
            "data_dir": "~/.local/share/photo-explorer",
            "cache_dir": "~/.cache/photo-explorer",
            "thumbnail_quality": request.thumbnail_quality or 85,
            "clip_model": request.clip_model or "ViT-B/32",
            "face_detection_enabled": request.face_detection_enabled if request.face_detection_enabled is not None else True,
            "auto_index_new_photos": request.auto_index_new_photos if request.auto_index_new_photos is not None else True,
            "thumbnail_cache_hours": request.thumbnail_cache_hours or 24,
            "indexing_batch_size": request.indexing_batch_size or 100,
            "indexing_parallel_workers": request.indexing_parallel_workers or 4,
            "default_sync_interval_hours": request.default_sync_interval_hours or 6,
        },
    )


@router.get("/storage", response_model=StorageStatsResponse)
async def get_storage_stats() -> StorageStatsResponse:
    """Get storage usage statistics.

    NOTE: This is a placeholder endpoint returning zeros.
    GitHub Issue: Implement actual storage statistics calculation.
    Should query database for photo counts and filesystem for storage usage.
    """
    # GitHub Issue: Inject SettingsUseCases for real storage stats
    return StorageStatsResponse(
        success=True,
        data={
            "total_photos": 0,
            "local_photos": 0,
            "remote_photos": 0,
            "storage_used_bytes": 0,
            "thumbnails_cached": 0,
            "cache_size_bytes": 0,
        },
    )
