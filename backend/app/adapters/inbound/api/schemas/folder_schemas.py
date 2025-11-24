"""Folder API schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class FolderCreateRequest(BaseModel):
    """Request to register a folder."""

    path: str = Field(..., min_length=1, max_length=4096, description="Folder path")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Folder name")
    recursive: bool = Field(True, description="Scan subdirectories recursively")
    auto_album: bool = Field(False, description="Create albums from folder structure")

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
        if ".." in v:
            raise ValueError("Path traversal patterns are not allowed")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate folder name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Folder name cannot be empty or whitespace only")
            if len(v) > 255:
                raise ValueError("Folder name must be at most 255 characters")
            return v
        return None


class FolderStats(BaseModel):
    """Folder processing statistics."""

    total_files: int
    processed: int
    pending: int
    failed: int


class FolderData(BaseModel):
    """Folder data for API responses."""

    id: str
    path: str
    name: Optional[str] = None
    recursive: bool
    auto_album: bool
    stats: Optional[FolderStats] = None
    last_scanned_at: Optional[str] = None
    created_at: str


class FolderResponse(BaseModel):
    """Response for single folder."""

    success: bool
    data: FolderData
    error: Optional[dict[str, Any]] = None


class FolderListData(BaseModel):
    """Folder list response data."""

    folders: list[FolderData]


class FolderListResponse(BaseModel):
    """Response for folder list."""

    success: bool
    data: FolderListData
    error: Optional[dict[str, Any]] = None
