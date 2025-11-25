"""Album API schemas."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AlbumCreateRequest(BaseModel):
    """Request to create an album."""

    name: str = Field(..., min_length=1, max_length=255, description="Album name")
    description: Optional[str] = Field(None, max_length=2000, description="Album description")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate album name."""
        v = v.strip()
        if not v:
            raise ValueError("Album name cannot be empty or whitespace only")
        if len(v) > 255:
            raise ValueError("Album name must be at most 255 characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate album description."""
        if v is not None:
            v = v.strip()
            if len(v) > 2000:
                raise ValueError("Album description must be at most 2000 characters")
            return v if v else None
        return None


class AlbumUpdateRequest(BaseModel):
    """Request to update an album."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Album name")
    description: Optional[str] = Field(None, max_length=2000, description="Album description")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate album name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Album name cannot be empty or whitespace only")
            if len(v) > 255:
                raise ValueError("Album name must be at most 255 characters")
            return v
        return None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate album description."""
        if v is not None:
            v = v.strip()
            if len(v) > 2000:
                raise ValueError("Album description must be at most 2000 characters")
            return v if v else None
        return None


class AlbumPhotosRequest(BaseModel):
    """Request to add/remove photos from album."""

    photo_ids: list[UUID] = Field(
        ..., min_length=1, max_length=1000, description="List of photo IDs"
    )

    @field_validator("photo_ids")
    @classmethod
    def validate_photo_ids(cls, v: list[UUID]) -> list[UUID]:
        """Validate photo IDs list."""
        if not v:
            raise ValueError("At least one photo ID is required")
        if len(v) > 1000:
            raise ValueError("Cannot process more than 1000 photos at once")
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate photo IDs are not allowed")
        return v


class AlbumData(BaseModel):
    """Album data for API responses."""

    id: str
    name: str
    description: Optional[str] = None
    cover_photo_id: Optional[str] = None
    photo_count: int
    created_at: str
    updated_at: Optional[str] = None


class AlbumResponse(BaseModel):
    """Response for single album."""

    success: bool
    data: AlbumData
    error: Optional[dict[str, Any]] = None


class AlbumListData(BaseModel):
    """Album list response data."""

    albums: list[AlbumData]


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    per_page: int
    total: int


class AlbumListResponse(BaseModel):
    """Response for album list."""

    success: bool
    data: AlbumListData
    meta: PaginationMeta
    error: Optional[dict[str, Any]] = None
