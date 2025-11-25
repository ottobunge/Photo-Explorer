"""Connector API schemas."""

import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ConnectorData(BaseModel):
    """Connector data for API responses."""

    id: str
    type: str
    name: str
    enabled: bool
    status: str
    config: dict[str, Any]
    last_sync: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class ConnectorResponse(BaseModel):
    """Response for single connector."""

    success: bool
    data: ConnectorData
    error: Optional[dict[str, Any]] = None


class ConnectorListData(BaseModel):
    """Connector list data."""

    connectors: list[ConnectorData]


class ConnectorListResponse(BaseModel):
    """Response for connector list."""

    success: bool
    data: ConnectorListData
    error: Optional[dict[str, Any]] = None


class ConnectorCreateRequest(BaseModel):
    """Request to create a connector."""

    type: str = Field(..., min_length=1, max_length=50, description="Connector type")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Connector name")
    config: dict[str, Any] = Field(default_factory=dict, description="Connector configuration")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate connector type."""
        allowed_types = {"local", "google_photos", "dropbox", "onedrive"}
        v = v.strip().lower()
        if v not in allowed_types:
            raise ValueError(f"Invalid connector type. Allowed: {', '.join(sorted(allowed_types))}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate connector name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Connector name cannot be empty or whitespace only")
            if len(v) > 255:
                raise ValueError("Connector name must be at most 255 characters")
            return v
        return None


class ConnectorUpdateRequest(BaseModel):
    """Request to update a connector."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Connector name")
    enabled: Optional[bool] = Field(None, description="Enable/disable connector")
    config: Optional[dict[str, Any]] = Field(None, description="Connector configuration")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate connector name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Connector name cannot be empty or whitespace only")
            if len(v) > 255:
                raise ValueError("Connector name must be at most 255 characters")
            return v
        return None


class LocalFolderCreateRequest(BaseModel):
    """Request to create a local folder connector."""

    path: str = Field(..., min_length=1, max_length=4096, description="Folder path")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Connector name")
    recursive: bool = Field(True, description="Scan subdirectories recursively")
    watch: bool = Field(True, description="Watch for file system changes")
    auto_album: bool = Field(False, description="Automatically create albums from folder structure")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate folder path."""
        v = v.strip()
        if not v:
            raise ValueError("Folder path cannot be empty")
        if len(v) > 4096:
            raise ValueError("Folder path must be at most 4096 characters")
        # Check for path traversal attempts
        if ".." in v or v.startswith("~"):
            # Allow tilde expansion but validate it's not malicious
            if v.startswith("~") and (len(v) == 1 or v[1] == "/"):
                pass  # Valid tilde usage
            elif ".." in v:
                raise ValueError("Path traversal patterns are not allowed")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate connector name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Connector name cannot be empty or whitespace only")
            if len(v) > 255:
                raise ValueError("Connector name must be at most 255 characters")
            return v
        return None


class SyncStatsData(BaseModel):
    """Sync statistics data."""

    total_items: int
    indexed: int
    skipped: int
    failed: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    is_complete: bool = False
    success_rate: float = 1.0


class SyncStatusData(BaseModel):
    """Sync status data."""

    syncing: bool
    last_sync: Optional[str] = None
    stats: Optional[SyncStatsData] = None


class SyncStatusResponse(BaseModel):
    """Response for sync status."""

    success: bool
    data: SyncStatusData
    error: Optional[dict[str, Any]] = None


class GooglePhotosAuthUrlData(BaseModel):
    """Google Photos auth URL data."""

    auth_url: str


class GooglePhotosAuthUrlResponse(BaseModel):
    """Response for Google Photos auth URL."""

    success: bool
    data: GooglePhotosAuthUrlData
    error: Optional[dict[str, Any]] = None


class GooglePhotosCallbackRequest(BaseModel):
    """Request for Google Photos OAuth callback."""

    code: str = Field(..., min_length=1, max_length=2048, description="OAuth authorization code")
    redirect_uri: str = Field(..., min_length=1, max_length=2048, description="OAuth redirect URI")
    state: Optional[str] = Field(None, max_length=256, description="CSRF state parameter")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate authorization code."""
        v = v.strip()
        if not v:
            raise ValueError("Authorization code cannot be empty")
        if len(v) > 2048:
            raise ValueError("Authorization code is too long")
        return v

    @field_validator("redirect_uri")
    @classmethod
    def validate_redirect_uri(cls, v: str) -> str:
        """Validate redirect URI."""
        v = v.strip()
        if not v:
            raise ValueError("Redirect URI cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Redirect URI must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("Redirect URI is too long")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Validate state parameter."""
        if v is not None:
            v = v.strip()
            if len(v) > 256:
                raise ValueError("State parameter is too long")
            return v if v else None
        return None


class GooglePhotosStatusData(BaseModel):
    """Google Photos status data."""

    connected: bool
    connector_id: Optional[str] = None
    email: Optional[str] = None
    photos_indexed: int = 0
    last_sync: Optional[str] = None


class GooglePhotosStatusResponse(BaseModel):
    """Response for Google Photos status."""

    success: bool
    data: GooglePhotosStatusData
    error: Optional[dict[str, Any]] = None
