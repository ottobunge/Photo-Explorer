"""Album API routes."""

from typing import Annotated
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


@router.post(
    "",
    response_model=AlbumResponse,
    status_code=201,
    summary="Create album",
    description="""
    Create a new photo album for organizing photos.

    Albums are collections of photos that you can organize manually or automatically.
    They provide a way to group related photos together for easy access and sharing.

    **Use cases:**
    - Organize photos by event (e.g., "Birthday Party 2024")
    - Group photos by topic (e.g., "Travel", "Family", "Work")
    - Create curated collections
    - Auto-generate albums from folder structure (with local connectors)

    **Properties:**
    - **name** (required): Album display name
    - **description** (optional): Longer description of the album's content

    After creating an album, use the add photos endpoint to populate it.
    """,
    responses={
        201: {
            "description": "Album created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Summer Vacation 2024",
                            "description": "Photos from our trip to Hawaii",
                            "cover_photo_id": None,
                            "photo_count": 0,
                            "created_at": "2024-01-20T10:00:00Z",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Invalid request (e.g., name too long)",
            "content": {"application/json": {"example": {"detail": "Album name is required"}}},
        },
    },
    tags=["Albums"],
)
async def create_album(
    request: AlbumCreateRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Create a new album."""
    from app.domain.entities import Album

    # Create the album
    album = Album.create(
        name=request.name,
        description=request.description,
    )

    # Save to database
    album = await album_repo.save(album)

    return AlbumResponse(
        success=True,
        data={
            "id": str(album.id.value),
            "name": album.name,
            "description": album.description,
            "cover_photo_id": str(album.cover_photo_id) if album.cover_photo_id else None,
            "photo_count": album.photo_count,
            "created_at": album.created_at.isoformat(),
        },
    )


@router.get(
    "",
    response_model=AlbumListResponse,
    summary="List albums",
    description="""
    Get a paginated list of all albums in the library.

    Returns album metadata including:
    - Album ID, name, and description
    - Photo count (number of photos in the album)
    - Cover photo ID (if set)
    - Creation timestamp

    **Use cases:**
    - Display album gallery in UI
    - Browse photo collections
    - Album selection for adding photos

    Results are paginated for performance with large album collections.
    """,
    responses={
        200: {
            "description": "List of albums",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "albums": [
                                {
                                    "id": "123e4567-e89b-12d3-a456-426614174000",
                                    "name": "Summer Vacation 2024",
                                    "description": "Photos from our trip to Hawaii",
                                    "cover_photo_id": "550e8400-e29b-41d4-a716-446655440000",
                                    "photo_count": 127,
                                    "created_at": "2024-01-20T10:00:00Z",
                                },
                                {
                                    "id": "223e4567-e89b-12d3-a456-426614174001",
                                    "name": "Birthday Party",
                                    "description": None,
                                    "cover_photo_id": None,
                                    "photo_count": 45,
                                    "created_at": "2024-01-15T14:30:00Z",
                                },
                            ]
                        },
                        "meta": {"page": 1, "per_page": 20, "total": 15},
                    }
                }
            },
        }
    },
    tags=["Albums"],
)
async def list_albums(
    album_repo: AlbumRepoDep,
    page: Annotated[int, Query(ge=1, le=1000, description="Page number (1-1000)")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page (1-100)")] = 20,
) -> AlbumListResponse:
    """List all albums with pagination."""
    offset = (page - 1) * per_page

    # Get albums from repository
    albums = await album_repo.find_all(limit=per_page, offset=offset)
    total = await album_repo.count()

    # Convert to response format
    album_data = [
        {
            "id": str(album.id.value),
            "name": album.name,
            "description": album.description,
            "cover_photo_id": str(album.cover_photo_id) if album.cover_photo_id else None,
            "photo_count": album.photo_count,
            "created_at": album.created_at.isoformat(),
        }
        for album in albums
    ]

    return AlbumListResponse(
        success=True,
        data={"albums": album_data},
        meta={"page": page, "per_page": per_page, "total": total},
    )


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: UUID,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Get an album by ID."""
    album = await album_repo.find_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    return AlbumResponse(
        success=True,
        data={
            "id": str(album.id.value),
            "name": album.name,
            "description": album.description,
            "cover_photo_id": str(album.cover_photo_id) if album.cover_photo_id else None,
            "photo_count": album.photo_count,
            "created_at": album.created_at.isoformat(),
        },
    )


@router.patch("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: UUID,
    request: AlbumUpdateRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Update an album."""
    album = await album_repo.find_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Update album details
    album.update(name=request.name, description=request.description)

    # Save updated album
    album = await album_repo.save(album)

    return AlbumResponse(
        success=True,
        data={
            "id": str(album.id.value),
            "name": album.name,
            "description": album.description,
            "cover_photo_id": str(album.cover_photo_id) if album.cover_photo_id else None,
            "photo_count": album.photo_count,
            "created_at": album.created_at.isoformat(),
        },
    )


@router.delete("/{album_id}")
async def delete_album(
    album_id: UUID,
    album_repo: AlbumRepoDep,
) -> dict:
    """Delete an album (photos are not deleted)."""
    deleted = await album_repo.delete(album_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Album not found")

    return {"success": True, "data": {"deleted": True}}


@router.post("/{album_id}/photos", response_model=AlbumResponse)
async def add_photos_to_album(
    album_id: UUID,
    request: AlbumPhotosRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Add photos to an album."""
    album = await album_repo.find_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Add each photo to the album
    for photo_id in request.photo_ids:
        album.add_photo(photo_id)

    # Save updated album
    album = await album_repo.save(album)

    return AlbumResponse(
        success=True,
        data={
            "id": str(album.id.value),
            "name": album.name,
            "description": album.description,
            "cover_photo_id": str(album.cover_photo_id) if album.cover_photo_id else None,
            "photo_count": album.photo_count,
            "created_at": album.created_at.isoformat(),
        },
    )


@router.delete("/{album_id}/photos")
async def remove_photos_from_album(
    album_id: UUID,
    request: AlbumPhotosRequest,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Remove photos from an album."""
    album = await album_repo.find_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Remove each photo from the album
    for photo_id in request.photo_ids:
        album.remove_photo(photo_id)

    # Save updated album
    album = await album_repo.save(album)

    return AlbumResponse(
        success=True,
        data={
            "id": str(album.id.value),
            "name": album.name,
            "description": album.description,
            "cover_photo_id": str(album.cover_photo_id) if album.cover_photo_id else None,
            "photo_count": album.photo_count,
            "created_at": album.created_at.isoformat(),
        },
    )


@router.post("/{album_id}/cover/{photo_id}", response_model=AlbumResponse)
async def set_album_cover(
    album_id: UUID,
    photo_id: UUID,
    album_repo: AlbumRepoDep,
) -> AlbumResponse:
    """Set the cover photo for an album."""
    album = await album_repo.find_by_id(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    try:
        # Set the cover photo
        album.set_cover(photo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save updated album
    album = await album_repo.save(album)

    return AlbumResponse(
        success=True,
        data={
            "id": str(album.id.value),
            "name": album.name,
            "description": album.description,
            "cover_photo_id": str(album.cover_photo_id) if album.cover_photo_id else None,
            "photo_count": album.photo_count,
            "created_at": album.created_at.isoformat(),
        },
    )
