"""Album API routes."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.adapters.inbound.api.schemas.album_schemas import (
    AlbumCreateRequest,
    AlbumListResponse,
    AlbumPhotosRequest,
    AlbumResponse,
    AlbumUpdateRequest,
)
from app.dependencies import AlbumRepoDep

router = APIRouter()


@router.post("", response_model=AlbumResponse, status_code=201)
async def create_album(
    request: AlbumCreateRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Create a new album."""
    # TODO: Implement album creation logic
    return AlbumResponse(
        success=True,
        data={
            "id": "placeholder-uuid",
            "name": request.name,
            "description": request.description,
            "cover_photo_id": None,
            "photo_count": 0,
            "created_at": "2024-01-01T00:00:00Z",
        },
    )


@router.get("", response_model=AlbumListResponse)
async def list_albums(
    album_repo: AlbumRepoDep,
    page: Annotated[int, Query(ge=1, le=1000, description="Page number (1-1000)")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page (1-100)")] = 20,
) -> AlbumListResponse:
    """List all albums with pagination."""
    # TODO: Implement album listing logic
    return AlbumListResponse(
        success=True,
        data={"albums": []},
        meta={"page": page, "per_page": per_page, "total": 0},
    )


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: UUID,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Get an album by ID."""
    # TODO: Implement album retrieval logic
    raise HTTPException(status_code=404, detail="Album not found")


@router.patch("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: UUID,
    request: AlbumUpdateRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Update an album."""
    # TODO: Implement album update logic
    raise HTTPException(status_code=404, detail="Album not found")


@router.delete("/{album_id}")
async def delete_album(
    album_id: UUID,
    album_repo: AlbumRepoDep,
) -> dict:
    """Delete an album (photos are not deleted)."""
    # TODO: Implement album deletion logic
    return {"success": True, "data": {"deleted": True}}


@router.post("/{album_id}/photos", response_model=AlbumResponse)
async def add_photos_to_album(
    album_id: UUID,
    request: AlbumPhotosRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Add photos to an album."""
    # TODO: Implement add photos to album logic
    raise HTTPException(status_code=404, detail="Album not found")


@router.delete("/{album_id}/photos")
async def remove_photos_from_album(
    album_id: UUID,
    request: AlbumPhotosRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Remove photos from an album."""
    # TODO: Implement remove photos from album logic
    raise HTTPException(status_code=404, detail="Album not found")


@router.post("/{album_id}/cover/{photo_id}", response_model=AlbumResponse)
async def set_album_cover(
    album_id: UUID,
    photo_id: UUID,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Set the cover photo for an album."""
    # TODO: Implement set album cover logic
    raise HTTPException(status_code=404, detail="Album not found")
