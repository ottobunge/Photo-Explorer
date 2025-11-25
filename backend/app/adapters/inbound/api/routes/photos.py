"""Photo API routes."""

import io
import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.adapters.inbound.api.schemas.photo_schemas import (
    PhotoListResponse,
    PhotoResponse,
    PhotoUploadResponse,
)
from app.adapters.inbound.workers.tasks import process_photo_task
from app.domain.entities.connector import ConnectorType
from app.dependencies import (
    AlbumRepoDep,
    ConnectorRepoDep,
    FileStorageDep,
    PhotoRepoDep,
    PhotoServiceDep,
    SearchServiceDep,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=PhotoUploadResponse,
    status_code=201,
    summary="Upload photos",
    description="Upload one or more photo files to the library",
    response_description="Upload results with list of uploaded and failed files",
)
async def upload_photos(
    photo_service: PhotoServiceDep,
    album_repo: AlbumRepoDep,
    connector_repo: ConnectorRepoDep,
    files: Annotated[list[UploadFile], File(description="One or more image files to upload (max 100 at once)")],
    album_id: Annotated[Optional[UUID], Form(description="Optional album ID to add photos to")] = None,
) -> PhotoUploadResponse:
    """
    Upload one or more photos to the library.

    This endpoint accepts multipart/form-data with one or more image files.
    Each file is validated for proper image format (MIME type must start with "image/").
    Successfully uploaded photos are queued for background processing, which includes:
    - Thumbnail generation
    - EXIF metadata extraction
    - Scene classification
    - Embedding generation for semantic search
    - Face detection

    Args:
        files: List of image files to upload (JPEG, PNG, etc.)
        album_id: Optional album ID to add the uploaded photos to

    Returns:
        PhotoUploadResponse with:
        - uploaded: List of successfully queued photos with their IDs and status
        - failed: List of failed uploads with error details

    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "uploaded": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "photo.jpg",
                        "status": "processing"
                    }
                ],
                "failed": [
                    {
                        "filename": "document.pdf",
                        "error": "Invalid file type"
                    }
                ]
            }
        }
        ```

    Status Codes:
        201: Photos successfully queued for upload
        400: Invalid request (no files or invalid data)
        413: File size too large
        500: Server error during upload

    Note:
        - Maximum file size depends on server configuration
        - Photos are processed asynchronously in the background
        - Check processing_status field to track completion
    """
    uploaded = []
    failed = []

    # Validate number of files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Cannot upload more than 100 files at once")

    # Validate album exists if provided
    if album_id:
        album = await album_repo.find_by_id(album_id)
        if not album:
            raise HTTPException(status_code=404, detail=f"Album {album_id} not found")

    # Get default upload connector
    upload_connector = None
    upload_connector_id = None
    try:
        all_connectors = await connector_repo.find_all()
        upload_connectors = [c for c in all_connectors if c.type == ConnectorType.UPLOAD]
        if upload_connectors:
            upload_connector = upload_connectors[0]
            upload_connector_id = upload_connector.id.value
            logger.debug(f"Using upload connector: {upload_connector_id}")
        else:
            logger.warning("No upload connector found, photos will be orphaned")
    except Exception as e:
        logger.warning(f"Failed to fetch upload connector: {e}", exc_info=True)
        # Continue without connector - photos will be created with connector_type="local" and no connector_id

    # Allowed MIME types for images
    allowed_mime_types = {
        "image/jpeg", "image/jpg", "image/png", "image/gif",
        "image/webp", "image/bmp", "image/tiff", "image/heic", "image/heif"
    }
    # Maximum file size: 50MB
    max_file_size = 50 * 1024 * 1024

    for file in files:
        try:
            # Validate filename
            if not file.filename:
                failed.append({
                    "filename": "unknown",
                    "error": "Filename is required",
                })
                continue

            # Sanitize filename length
            if len(file.filename) > 255:
                failed.append({
                    "filename": file.filename[:50] + "...",
                    "error": "Filename is too long (max 255 characters)",
                })
                continue

            # Validate file type
            if not file.content_type:
                failed.append({
                    "filename": file.filename,
                    "error": "Content type is required",
                })
                continue

            if file.content_type.lower() not in allowed_mime_types:
                failed.append({
                    "filename": file.filename,
                    "error": f"Invalid file type: {file.content_type}. Allowed: {', '.join(sorted(allowed_mime_types))}",
                })
                continue

            # Read file content
            file_content = await file.read()
            if not file_content:
                failed.append({
                    "filename": file.filename,
                    "error": "Empty file",
                })
                continue

            # Validate file size
            if len(file_content) > max_file_size:
                failed.append({
                    "filename": file.filename,
                    "error": f"File size exceeds maximum of {max_file_size // (1024 * 1024)}MB",
                })
                continue

            # Upload photo using photo service
            file_obj = io.BytesIO(file_content)
            photo = await photo_service.upload_photo(
                file=file_obj,
                filename=file.filename or "unnamed.jpg",
                content_type=file.content_type,
                album_id=album_id,
                connector_type=ConnectorType.UPLOAD.value if upload_connector else "local",
                connector_id=upload_connector_id,
            )

            # Queue background processing task
            process_photo_task.delay(str(photo.id.value))

            logger.info(
                f"Photo uploaded and queued for processing",
                extra={
                    "photo_id": str(photo.id.value),
                    "photo_filename": photo.filename,
                    "album_id": str(album_id) if album_id else None,
                },
            )

            uploaded.append({
                "id": str(photo.id.value),
                "filename": photo.filename,
                "status": "processing",
            })

        except Exception as e:
            logger.error(
                f"Failed to upload photo",
                extra={
                    "photo_filename": file.filename or "unknown",
                    "error": str(e),
                },
                exc_info=True,
            )
            failed.append({
                "filename": file.filename or "unknown",
                "error": f"Upload failed: {str(e)}",
            })

    return PhotoUploadResponse(
        success=True,
        data={"uploaded": uploaded, "failed": failed},
    )


@router.get(
    "",
    response_model=PhotoListResponse,
    summary="List photos",
    description="Get a paginated list of photos with optional filters",
    response_description="Paginated list of photos with metadata",
)
async def list_photos(
    photo_repo: PhotoRepoDep,
    page: Annotated[int, Query(ge=1, le=1000, description="Page number (1-indexed)")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Number of items per page")] = 20,
    album_id: Annotated[Optional[UUID], Query(description="Filter by album ID")] = None,
    connector_id: Annotated[Optional[UUID], Query(description="Filter by connector ID (photo source)")] = None,
) -> PhotoListResponse:
    """
    List photos with pagination and optional filters.

    This endpoint returns a paginated list of all photos in the library.
    Results can be filtered by album or connector (photo source).
    Each photo includes metadata such as filename, dimensions, taken date,
    processing status, and scene classification.

    Args:
        photo_repo: Photo repository dependency (injected)
        page: Page number (1-indexed), max 1000
        per_page: Number of items per page, max 100
        album_id: Optional - filter photos belonging to specific album
        connector_id: Optional - filter photos from specific connector

    Returns:
        PhotoListResponse containing:
        - data.photos: List of photo objects with full metadata
        - meta.page: Current page number
        - meta.per_page: Items per page
        - meta.total: Total number of photos matching filters

    Example Request:
        ```
        GET /api/v1/photos?page=1&per_page=20&connector_id=550e8400-e29b-41d4-a716-446655440000
        ```

    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "photos": [
                    {
                        "id": "650e8400-e29b-41d4-a716-446655440001",
                        "filename": "IMG_1234.jpg",
                        "thumbnail_url": "/api/v1/photos/650e8400-e29b-41d4-a716-446655440001/thumbnail",
                        "width": 4032,
                        "height": 3024,
                        "taken_at": "2024-01-15T14:30:00Z",
                        "scene_type": "outdoor",
                        "is_indoor": false,
                        "processing_status": "completed",
                        "connector_type": "google_photos"
                    }
                ]
            },
            "meta": {
                "page": 1,
                "per_page": 20,
                "total": 150
            }
        }
        ```

    Status Codes:
        200: Success
        400: Invalid query parameters
        500: Server error
    """
    # Calculate offset
    offset = (page - 1) * per_page

    # Get photos (find_all supports optional album_id and connector_id filtering)
    photos = await photo_repo.find_all(
        limit=per_page, offset=offset, album_id=album_id, connector_id=connector_id
    )
    total = await photo_repo.count(album_id=album_id, connector_id=connector_id)

    # Convert to response format
    photo_list = []
    for photo in photos:
        photo_list.append({
            "id": photo.id.value,
            "filename": photo.filename,
            "original_path": photo.source_path,
            "storage_path": photo.storage_path,
            "thumbnail_path": photo.thumbnail_path,
            "thumbnail_url": f"/api/v1/photos/{photo.id.value}/thumbnail" if photo.thumbnail_path or photo.is_remote else None,
            "mime_type": photo.mime_type,
            "file_size": photo.file_size,
            "width": photo.width,
            "height": photo.height,
            "taken_at": photo.taken_at,
            "description": photo.description,
            "scene_type": photo.scene_classification.scene_type if photo.scene_classification else None,
            "is_indoor": photo.scene_classification.is_indoor if photo.scene_classification else None,
            "detected_objects": photo.detected_objects or [],
            "processing_status": photo.processing_status,
            "connector_type": photo.connector_type,
            "created_at": photo.created_at,
            "updated_at": photo.updated_at,
        })

    return PhotoListResponse(
        success=True,
        data={"photos": photo_list},
        meta={"page": page, "per_page": per_page, "total": total},
    )


@router.get(
    "/{photo_id}",
    response_model=PhotoResponse,
    summary="Get photo details",
    description="Get complete metadata for a single photo by ID",
    response_description="Photo details with all metadata and relationships",
)
async def get_photo(
    photo_id: UUID,
    photo_service: PhotoServiceDep,
) -> PhotoResponse:
    """
    Get a single photo by ID with complete metadata.

    This endpoint retrieves complete information about a photo including:
    - File metadata (size, dimensions, MIME type)
    - EXIF data (camera info, GPS, etc.)
    - AI-generated content (description, scene classification, detected objects)
    - Processing status
    - Relationships (albums, faces, connector)

    Args:
        photo_id: UUID of the photo to retrieve

    Returns:
        PhotoResponse with complete photo data

    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "filename": "IMG_1234.jpg",
                "storage_path": "/storage/photos/2024/01/IMG_1234.jpg",
                "thumbnail_url": "/api/v1/photos/650e8400-e29b-41d4-a716-446655440001/thumbnail",
                "mime_type": "image/jpeg",
                "file_size": 3145728,
                "width": 4032,
                "height": 3024,
                "taken_at": "2024-01-15T14:30:00Z",
                "description": "A scenic mountain landscape with snow-covered peaks",
                "scene_type": "outdoor",
                "is_indoor": false,
                "detected_objects": ["mountain", "sky", "snow"],
                "processing_status": "completed",
                "connector_type": "google_photos",
                "created_at": "2024-01-20T10:00:00Z",
                "updated_at": "2024-01-20T10:05:00Z"
            }
        }
        ```

    Status Codes:
        200: Photo found and returned
        404: Photo not found
        500: Server error
    """
    photo = await photo_service.get_photo(photo_id)

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Build response data with all metadata
    photo_data = {
        "id": photo.id.value,
        "filename": photo.filename,
        "original_path": photo.source_path,
        "storage_path": photo.storage_path,
        "thumbnail_path": photo.thumbnail_path,
        "thumbnail_url": f"/api/v1/photos/{photo.id.value}/thumbnail" if photo.thumbnail_path or photo.is_remote else None,
        "mime_type": photo.mime_type,
        "file_size": photo.file_size,
        "width": photo.width,
        "height": photo.height,
        "taken_at": photo.taken_at,
        "exif_data": photo.exif.to_dict() if photo.exif else None,
        "description": photo.description,
        "scene_type": photo.scene_classification.scene_type if photo.scene_classification else None,
        "is_indoor": photo.scene_classification.is_indoor if photo.scene_classification else None,
        "detected_objects": photo.detected_objects or [],
        "processing_status": photo.processing_status,
        "connector_type": photo.connector_type,
        "created_at": photo.created_at,
        "updated_at": photo.updated_at,
    }

    return PhotoResponse(success=True, data=photo_data)


@router.delete(
    "/{photo_id}",
    summary="Delete photo",
    description="Delete a photo and all associated data",
    response_description="Deletion confirmation",
)
async def delete_photo(
    photo_id: UUID,
    photo_service: PhotoServiceDep,
) -> dict:
    """
    Delete a photo and all associated data.

    This endpoint permanently deletes a photo and cascades to:
    - Remove photo embedding from vector store (Qdrant)
    - Delete physical files (original photo and thumbnail) from storage
    - Cascade delete related database records (faces, album associations)
    - Remove from search index

    This operation is irreversible. The photo and all associated data
    will be permanently removed from the system.

    Args:
        photo_id: UUID of the photo to delete

    Returns:
        Success confirmation with deletion status

    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "deleted": true
            }
        }
        ```

    Status Codes:
        200: Photo successfully deleted
        404: Photo not found
        500: Server error during deletion

    Note:
        - Database cascade rules handle deletion of related records (faces, album associations)
        - Vector embeddings are removed from Qdrant
        - Physical files are removed from storage
        - If file deletion fails, the database record is still removed (orphaned files can be cleaned up later)
    """
    deleted = await photo_service.delete_photo(photo_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Photo not found")

    logger.info(
        f"Photo deleted successfully",
        extra={"photo_id": str(photo_id)},
    )

    return {"success": True, "data": {"deleted": True}}


@router.get(
    "/{photo_id}/file",
    summary="Get original photo file",
    description="""
    Download the original, full-resolution photo file.

    This endpoint serves the original photo file as uploaded or imported.
    Unlike the thumbnail endpoint, this returns the full-resolution image
    with original quality and dimensions.

    The response includes appropriate caching headers for efficient delivery.
    Content-Type is set based on the original file's MIME type.

    Supported for:
    - Uploaded photos (stored locally)
    - Local folder photos (served from original path)
    - Google Photos (may require fetching from remote)
    """,
    responses={
        200: {
            "description": "Original photo file",
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/webp": {"schema": {"type": "string", "format": "binary"}},
            }
        },
        404: {
            "description": "Photo not found or file not available",
            "content": {
                "application/json": {
                    "example": {"detail": "Photo not found or file not available"}
                }
            }
        }
    },
    tags=["Photos"]
)
async def get_photo_file(
    photo_id: UUID,
    photo_service: PhotoServiceDep,
) -> Response:
    """Get the original photo file."""
    result = await photo_service.get_photo_file(photo_id)

    if not result:
        raise HTTPException(status_code=404, detail="Photo not found or file not available")

    file_bytes, content_type = result

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": "inline",
        },
    )


@router.get(
    "/{photo_id}/thumbnail",
    summary="Get photo thumbnail",
    description="""
    Get a thumbnail (preview) image for a photo.

    Thumbnails are automatically generated during photo processing and are
    optimized for fast loading in galleries and lists. Typical dimensions
    are 300x300 pixels with JPEG compression.

    The response includes caching headers (24 hours) for optimal performance.
    Thumbnails are served as JPEG regardless of original format.

    Use cases:
    - Photo galleries and grids
    - Search results
    - Album previews
    - Face cluster representatives

    If the thumbnail hasn't been generated yet (photo still processing),
    this endpoint will return 404. Check the processing_status field in
    the photo metadata.
    """,
    responses={
        200: {
            "description": "Thumbnail image (JPEG)",
            "content": {
                "image/jpeg": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            },
            "headers": {
                "Cache-Control": {
                    "description": "Caching directive",
                    "schema": {"type": "string", "example": "public, max-age=86400"}
                }
            }
        },
        404: {
            "description": "Photo or thumbnail not found",
            "content": {
                "application/json": {
                    "examples": {
                        "photo_not_found": {
                            "summary": "Photo doesn't exist",
                            "value": {"detail": "Photo not found"}
                        },
                        "thumbnail_not_ready": {
                            "summary": "Thumbnail not generated yet",
                            "value": {"detail": "Thumbnail not available"}
                        },
                        "file_missing": {
                            "summary": "Thumbnail file missing",
                            "value": {"detail": "Thumbnail file not found"}
                        }
                    }
                }
            }
        }
    },
    tags=["Photos"]
)
async def get_photo_thumbnail(
    photo_id: UUID,
    photo_repo: PhotoRepoDep,
    file_storage: FileStorageDep,
) -> Response:
    """Get the photo thumbnail."""
    photo = await photo_repo.find_by_id(photo_id)

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    if not photo.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    try:
        thumbnail_data = await file_storage.get_file(photo.thumbnail_path)
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail file not found")

        return Response(
            content=thumbnail_data,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Thumbnail file not found")


@router.get(
    "/{photo_id}/similar",
    summary="Find similar photos",
    description="Find photos similar to the given photo using visual similarity",
    response_description="List of similar photos sorted by similarity score",
)
async def get_similar_photos(
    photo_id: UUID,
    search_service: SearchServiceDep,
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum number of results")] = 10,
) -> dict:
    """
    Find photos visually similar to the given photo.

    This endpoint uses vector similarity search to find photos that are
    visually similar to the specified photo. The similarity is based on
    CLIP embeddings generated during photo processing.

    The search:
    - Uses the photo's embedding vector stored in Qdrant
    - Performs nearest neighbor search in the vector space
    - Returns results sorted by similarity score (0.0 to 1.0)
    - Excludes the query photo itself from results

    Args:
        photo_id: UUID of the reference photo
        limit: Maximum number of similar photos to return (1-50, default 10)

    Returns:
        Dict containing success status and list of similar photos

    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "results": [
                    {
                        "photo": {
                            "id": "750e8400-e29b-41d4-a716-446655440002",
                            "filename": "IMG_5678.jpg",
                            "thumbnail_url": "/api/v1/photos/750e8400-e29b-41d4-a716-446655440002/thumbnail",
                            "scene_type": "outdoor",
                            "processing_status": "completed"
                        },
                        "score": 0.92,
                        "highlights": ["Similar content"]
                    }
                ]
            }
        }
        ```

    Status Codes:
        200: Success (returns empty list if no similar photos found)
        404: Reference photo not found or has no embedding
        500: Server error

    Note:
        - Photos must be processed (have embeddings) to appear in results
        - Similarity is based on visual content, not metadata
        - Higher scores indicate greater similarity (max 1.0)
    """
    try:
        similar_results = await search_service.find_similar(
            photo_id=photo_id,
            limit=limit,
        )

        # Convert results to response format
        results = []
        for result in similar_results:
            photo_data = {
                "id": result.photo.id.value,
                "filename": result.photo.filename,
                "original_path": result.photo.source_path,
                "storage_path": result.photo.storage_path,
                "thumbnail_path": result.photo.thumbnail_path,
                "thumbnail_url": (
                    f"/api/v1/photos/{result.photo.id.value}/thumbnail"
                    if result.photo.thumbnail_path or result.photo.is_remote
                    else None
                ),
                "mime_type": result.photo.mime_type,
                "file_size": result.photo.file_size,
                "width": result.photo.width,
                "height": result.photo.height,
                "taken_at": result.photo.taken_at,
                "description": result.photo.description,
                "scene_type": (
                    result.photo.scene_classification.scene_type
                    if result.photo.scene_classification
                    else None
                ),
                "is_indoor": (
                    result.photo.scene_classification.is_indoor
                    if result.photo.scene_classification
                    else None
                ),
                "detected_objects": result.photo.detected_objects or [],
                "processing_status": result.photo.processing_status,
                "connector_type": result.photo.connector_type,
                "created_at": result.photo.created_at,
                "updated_at": result.photo.updated_at,
            }
            results.append({
                "photo": photo_data,
                "score": result.score,
                "highlights": result.highlights,
            })

        logger.debug(
            f"Found {len(results)} similar photos",
            extra={
                "photo_id": str(photo_id),
                "limit": limit,
                "results_count": len(results),
            },
        )

        return {"success": True, "data": {"results": results}}

    except Exception as e:
        logger.error(
            f"Error finding similar photos",
            extra={
                "photo_id": str(photo_id),
                "error": str(e),
            },
            exc_info=True,
        )
        # Return empty results rather than failing
        # (photo might not have embedding yet)
        return {"success": True, "data": {"results": []}}
