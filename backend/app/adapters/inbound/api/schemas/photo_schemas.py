"""Photo API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PhotoData(BaseModel):
    """Photo data for API responses."""

    id: UUID = Field(description="Unique photo identifier")
    filename: str = Field(description="Original filename", example="IMG_1234.jpg")
    original_path: str | None = Field(
        None, description="Original file path", example="/path/to/IMG_1234.jpg"
    )
    storage_path: str | None = Field(
        None,
        description="Storage path (optional for remote photos)",
        example="/storage/photos/2024/01/IMG_1234.jpg",
    )
    thumbnail_path: str | None = Field(
        None, description="Thumbnail file path", example="/storage/thumbnails/IMG_1234_thumb.jpg"
    )
    thumbnail_url: str | None = Field(
        None,
        description="URL to fetch thumbnail",
        example="/api/v1/photos/650e8400-e29b-41d4-a716-446655440001/thumbnail",
    )
    mime_type: str | None = Field(None, description="MIME type", example="image/jpeg")
    file_size: int | None = Field(None, description="File size in bytes", example=3145728)
    width: int | None = Field(None, description="Image width in pixels", ge=1, example=4032)
    height: int | None = Field(None, description="Image height in pixels", ge=1, example=3024)
    taken_at: datetime | None = Field(
        None, description="When photo was taken", example="2024-01-15T14:30:00Z"
    )
    exif_data: dict[str, Any] | None = Field(
        None, description="EXIF metadata", example={"Make": "Canon", "Model": "EOS R5"}
    )
    description: str | None = Field(
        None,
        description="AI-generated description",
        example="A scenic mountain landscape with snow-covered peaks",
    )
    scene_type: str | None = Field(None, description="Scene classification", example="outdoor")
    is_indoor: bool | None = Field(
        None, description="Indoor/outdoor classification", example=False
    )
    detected_objects: list[str] = Field(
        default_factory=list, description="AI-detected objects", example=["mountain", "sky", "snow"]
    )
    processing_status: str = Field(
        description="Processing status: pending, processing, completed, failed",
        example="completed",
    )
    connector_type: str | None = Field(
        None, description="Source connector type", example="google_photos"
    )
    created_at: datetime = Field(
        description="When photo was added to library", example="2024-01-20T10:00:00Z"
    )
    updated_at: datetime | None = Field(
        None, description="Last update timestamp", example="2024-01-20T10:05:00Z"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "filename": "IMG_1234.jpg",
                "original_path": "/photos/IMG_1234.jpg",
                "storage_path": "/storage/photos/2024/01/IMG_1234.jpg",
                "thumbnail_path": "/storage/thumbnails/IMG_1234_thumb.jpg",
                "thumbnail_url": "/api/v1/photos/650e8400-e29b-41d4-a716-446655440001/thumbnail",
                "mime_type": "image/jpeg",
                "file_size": 3145728,
                "width": 4032,
                "height": 3024,
                "taken_at": "2024-01-15T14:30:00Z",
                "exif_data": {"Make": "Canon", "Model": "EOS R5"},
                "description": "A scenic mountain landscape with snow-covered peaks",
                "scene_type": "outdoor",
                "is_indoor": False,
                "detected_objects": ["mountain", "sky", "snow"],
                "processing_status": "completed",
                "connector_type": "google_photos",
                "created_at": "2024-01-20T10:00:00Z",
                "updated_at": "2024-01-20T10:05:00Z",
            }
        }


class PhotoUploadedItem(BaseModel):
    """Single uploaded photo result."""

    id: str = Field(description="Photo UUID", example="650e8400-e29b-41d4-a716-446655440001")
    filename: str = Field(description="Uploaded filename", example="vacation.jpg")
    status: str = Field(description="Upload status", example="processing")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "filename": "vacation.jpg",
                "status": "processing",
            }
        }


class PhotoUploadData(BaseModel):
    """Upload response data."""

    uploaded: list[PhotoUploadedItem] = Field(description="Successfully uploaded photos")
    failed: list[dict[str, str]] = Field(description="Failed uploads with error messages")

    class Config:
        json_schema_extra = {
            "example": {
                "uploaded": [
                    {
                        "id": "650e8400-e29b-41d4-a716-446655440001",
                        "filename": "vacation.jpg",
                        "status": "processing",
                    }
                ],
                "failed": [
                    {"filename": "document.pdf", "error": "Invalid file type - must be an image"}
                ],
            }
        }


class PhotoUploadResponse(BaseModel):
    """Response for photo upload."""

    success: bool = Field(description="Whether the request succeeded", example=True)
    data: PhotoUploadData
    error: dict[str, Any] | None = Field(None, description="Error details if success is false")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "uploaded": [
                        {
                            "id": "650e8400-e29b-41d4-a716-446655440001",
                            "filename": "vacation.jpg",
                            "status": "processing",
                        }
                    ],
                    "failed": [],
                },
            }
        }


class PhotoListData(BaseModel):
    """Photo list response data."""

    photos: list[PhotoData] = Field(description="List of photos")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(description="Current page number (1-indexed)", ge=1, example=1)
    per_page: int = Field(description="Items per page", ge=1, le=100, example=20)
    total: int = Field(description="Total number of items", ge=0, example=150)

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "per_page": 20,
                "total": 150,
            }
        }


class PhotoListResponse(BaseModel):
    """Response for photo list."""

    success: bool = Field(description="Whether the request succeeded", example=True)
    data: PhotoListData
    meta: PaginationMeta
    error: dict[str, Any] | None = Field(None, description="Error details if success is false")


class PhotoResponse(BaseModel):
    """Response for single photo."""

    success: bool = Field(description="Whether the request succeeded", example=True)
    data: PhotoData
    error: dict[str, Any] | None = Field(None, description="Error details if success is false")
