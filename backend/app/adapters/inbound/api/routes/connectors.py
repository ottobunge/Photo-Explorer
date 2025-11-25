"""Connectors API routes."""

import logging
import os
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.adapters.inbound.api.schemas.connector_schemas import (
    ConnectorCreateRequest,
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorUpdateRequest,
    GooglePhotosAuthUrlResponse,
    GooglePhotosCallbackRequest,
    GooglePhotosStatusResponse,
    LocalFolderCreateRequest,
    SyncStatusResponse,
)
from app.adapters.outbound.connectors import GooglePhotosPickerClient
from app.adapters.outbound.storage import SecureTokenStorage
from app.dependencies import ConnectorRepoDep, DbSession, PhotoRepoDep

router = APIRouter()
logger = logging.getLogger(__name__)

# Get Google OAuth credentials from environment
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_API_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_API_CLIENT_SECRET", "")


# ===================
# Pydantic models for Picker API
# ===================


class PickerSessionResponse(BaseModel):
    """Response for picker session creation."""

    success: bool
    data: dict


class PickerSessionStatusResponse(BaseModel):
    """Response for picker session status."""

    success: bool
    data: dict


# ===================
# General Connectors
# ===================


@router.get("", response_model=ConnectorListResponse)
async def list_connectors(
    connector_repo: ConnectorRepoDep,
) -> ConnectorListResponse:
    """List all configured connectors."""
    connectors = await connector_repo.find_all()

    connector_data = [
        {
            "id": str(c.id.value),
            "type": c.type.value,
            "name": c.name,
            "enabled": c.enabled,
            "status": c.status.value,
            "config": c.config,
            "last_sync": c.last_sync.isoformat() if c.last_sync else None,
            "error_message": c.error_message,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in connectors
    ]

    return ConnectorListResponse(
        success=True,
        data={"connectors": connector_data},
    )


@router.get("/{connector_id}", response_model=ConnectorResponse)
async def get_connector(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> ConnectorResponse:
    """Get a specific connector."""
    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    return ConnectorResponse(
        success=True,
        data={
            "id": str(connector.id.value),
            "type": connector.type.value,
            "name": connector.name,
            "enabled": connector.enabled,
            "status": connector.status.value,
            "config": connector.config,
            "last_sync": connector.last_sync.isoformat() if connector.last_sync else None,
            "error_message": connector.error_message,
            "created_at": connector.created_at.isoformat(),
            "updated_at": connector.updated_at.isoformat() if connector.updated_at else None,
        },
    )


@router.get("/{connector_id}/photos")
async def get_connector_photos(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
    photo_repo: PhotoRepoDep,
    page: Annotated[int, Query(ge=1, le=1000, description="Page number (1-1000)")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page (1-100)")] = 20,
) -> dict:
    """Get all photos from a specific connector."""
    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Get photos for this connector
    offset = (page - 1) * per_page
    photos = await photo_repo.find_by_connector(connector_id, limit=per_page, offset=offset)
    total = await photo_repo.count_by_connector(connector_id)

    photo_list = [
        {
            "id": str(photo.id.value),
            "filename": photo.filename,
            "connector_id": str(photo.connector_id) if photo.connector_id else None,
            "thumbnail_url": f"/api/v1/photos/{photo.id.value}/thumbnail"
            if photo.thumbnail_path or photo.is_remote
            else None,
            "taken_at": photo.taken_at.isoformat() if photo.taken_at else None,
            "processing_status": photo.processing_status,
            "created_at": photo.created_at.isoformat(),
        }
        for photo in photos
    ]

    return {
        "photos": photo_list,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.patch("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: UUID,
    request: ConnectorUpdateRequest,
    connector_repo: ConnectorRepoDep,
) -> ConnectorResponse:
    """Update a connector's configuration."""
    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Update fields using domain methods
    if request.name is not None:
        connector.name = request.name
        connector._touch()  # Update timestamp

    if request.enabled is not None:
        # Use domain methods instead of direct mutation
        if request.enabled:
            connector.enable()
        else:
            connector.disable()

    if request.config is not None:
        # Use domain method for config updates
        connector.update_config(request.config)

    # Save updated connector (timestamp already updated by domain methods)
    updated = await connector_repo.save(connector)

    return ConnectorResponse(
        success=True,
        data={
            "id": str(updated.id.value),
            "type": updated.type.value,
            "name": updated.name,
            "enabled": updated.enabled,
            "status": updated.status.value,
            "config": updated.config,
            "last_sync": updated.last_sync.isoformat() if updated.last_sync else None,
            "error_message": updated.error_message,
            "created_at": updated.created_at.isoformat(),
            "updated_at": updated.updated_at.isoformat() if updated.updated_at else None,
        },
    )


@router.delete("/{connector_id}")
async def delete_connector(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
    photo_repo: PhotoRepoDep,
    db_session: DbSession,
    delete_photos: Annotated[bool, Query(description="Also delete indexed photos")] = False,
) -> dict:
    """Delete a connector.

    Uses transaction management to ensure atomic deletion:
    - All operations succeed together, or all are rolled back
    - Prevents partial deletions and data corruption
    """
    from app.domain.entities.connector import ConnectorType

    try:
        connector = await connector_repo.find_by_id(connector_id)
        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        logger.info(
            "Deleting connector",
            extra={
                "connector_id": str(connector_id),
                "connector_type": connector.type.value,
                "connector_name": connector.name,
                "delete_photos": delete_photos,
            },
        )

        # Delete associated tokens if it's a Google Photos connector
        # Note: Token deletion is outside transaction (file system operation)
        # but tokens can be safely re-created if needed
        if connector.type == ConnectorType.GOOGLE_PHOTOS:
            token_storage = SecureTokenStorage()
            await token_storage.delete_tokens(f"google_photos_{connector_id}")

        # All database operations within transaction
        # Delete associated photos if requested
        photo_count = 0
        if delete_photos:
            # Get all photos from this connector
            photos = await photo_repo.find_by_connector(connector_id, limit=10000, offset=0)
            photo_count = len(photos)
            for photo in photos:
                await photo_repo.delete(photo.id.value)

        # Delete the connector (photos will be orphaned if delete_photos=False)
        deleted = await connector_repo.delete(connector_id)

        # Commit transaction - all operations succeed atomically
        await db_session.commit()

        logger.info(
            "Connector deleted successfully",
            extra={
                "connector_id": str(connector_id),
                "photos_deleted": photo_count if delete_photos else 0,
            },
        )

        return {
            "success": True,
            "message": f"Connector deleted. {'Photos deleted.' if delete_photos else 'Photos orphaned.'}",
        }
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        # Rollback transaction on any error
        await db_session.rollback()
        logger.error(
            "Failed to delete connector",
            extra={
                "connector_id": str(connector_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete connector: {str(e)}")


@router.post("/{connector_id}/sync")
async def trigger_sync(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> dict:
    """Trigger a manual sync for a connector."""
    from app.domain.entities.connector import ConnectorType

    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    if connector.type == ConnectorType.GOOGLE_PHOTOS:
        # Trigger Google Photos sync task
        from app.adapters.inbound.workers.tasks.google_photos_sync import sync_google_photos_task

        task = sync_google_photos_task.delay(str(connector_id))
        return {
            "success": True,
            "data": {
                "sync_triggered": True,
                "task_id": task.id,
            },
        }
    elif connector.type == ConnectorType.LOCAL:
        # Trigger local folder sync task
        from app.adapters.inbound.workers.tasks.connector_sync import sync_local_folder_task

        task = sync_local_folder_task.delay(str(connector_id))
        return {
            "success": True,
            "data": {
                "sync_triggered": True,
                "task_id": task.id,
            },
        }

    raise HTTPException(status_code=400, detail=f"Unknown connector type: {connector.type}")


@router.post("/{connector_id}/reprocess")
async def trigger_reprocess(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> dict:
    """
    Reprocess all photos from a connector (regenerate embeddings from thumbnails).

    This is useful for photos that were imported before embedding generation was enabled.
    """
    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Trigger reprocessing task
    from app.adapters.inbound.workers.tasks.photo_processing import reprocess_connector_photos_task

    task = reprocess_connector_photos_task.delay(str(connector_id))

    return {
        "success": True,
        "data": {
            "reprocess_triggered": True,
            "task_id": task.id,
            "message": "Reprocessing started. Embeddings will be generated in the background.",
        },
    }


@router.get("/{connector_id}/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> SyncStatusResponse:
    """Get the current sync status for a connector."""
    from app.domain.entities.connector import ConnectorStatus

    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    is_syncing = connector.status == ConnectorStatus.SYNCING

    stats = None
    if connector.last_sync_stats:
        stats = {
            "total_items": connector.last_sync_stats.total_items,
            "indexed": connector.last_sync_stats.indexed,
            "skipped": connector.last_sync_stats.skipped,
            "failed": connector.last_sync_stats.failed,
            "duration_seconds": connector.last_sync_stats.duration_seconds,
        }

    return SyncStatusResponse(
        success=True,
        data={
            "syncing": is_syncing,
            "last_sync": connector.last_sync.isoformat() if connector.last_sync else None,
            "stats": stats,
        },
    )


# ===================
# Google Photos
# ===================


@router.get("/google-photos/auth-url", response_model=GooglePhotosAuthUrlResponse)
async def get_google_photos_auth_url(
    redirect_uri: Annotated[
        str, Query(min_length=1, max_length=2048, description="OAuth callback URL")
    ],
    state: Annotated[
        Optional[str], Query(max_length=256, description="State parameter for CSRF protection")
    ] = None,
) -> GooglePhotosAuthUrlResponse:
    """Get the OAuth authorization URL for Google Photos (using Picker API)."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Set GOOGLE_API_CLIENT_ID environment variable.",
        )

    # Use Picker client which has scopes available for new projects
    client = GooglePhotosPickerClient(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )

    auth_url = client.get_auth_url(redirect_uri=redirect_uri, state=state)

    return GooglePhotosAuthUrlResponse(
        success=True,
        data={"auth_url": auth_url},
    )


@router.post("/google-photos/callback")
async def google_photos_oauth_callback(
    request: GooglePhotosCallbackRequest,
    connector_repo: ConnectorRepoDep,
) -> dict:
    """
    Exchange authorization code for tokens (using Picker API).

    This endpoint receives the authorization code from Google
    and exchanges it for access and refresh tokens.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured",
        )

    # Use Picker client
    client = GooglePhotosPickerClient(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )

    try:
        # Exchange code for tokens
        tokens = await client.exchange_code(
            code=request.code,
            redirect_uri=request.redirect_uri,
        )

        # Create new Google Photos connector (supports multiple accounts)
        from app.domain.entities.connector import Connector

        # Try to get the user's email from Google to name the connector
        connector_name = "Google Photos"
        email = None
        try:
            # Use the tokens to get user info
            client.set_tokens(tokens.access_token, tokens.refresh_token)
            user_info = await client.get_user_info()
            if user_info:
                email = user_info.get("email")
                if email:
                    connector_name = f"Google Photos ({email})"
        except Exception:
            pass  # Fall back to default name

        new_connector = Connector.create_google_photos(name=connector_name)
        new_connector.set_connected()
        # Store email in config for reference
        if email:
            new_connector.config["email"] = email
        connector = await connector_repo.save(new_connector)

        # Store tokens with connector-specific key
        token_storage = SecureTokenStorage()
        await token_storage.save_tokens(f"google_photos_{connector.id.value}", tokens)

        logger.info(
            "Google Photos connector created successfully",
            extra={
                "connector_id": str(connector.id.value),
                "connector_name": connector_name,
                "email": email,
            },
        )

        return {
            "success": True,
            "data": {
                "connected": True,
                "connector_id": str(connector.id.value),
                "expires_at": tokens.expires_at.isoformat(),
            },
        }

    except Exception as e:
        logger.error(
            "OAuth exchange failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {str(e)}")
    finally:
        await client.close()


@router.get("/google-photos/callback")
async def google_photos_oauth_callback_redirect(
    code: Annotated[
        str, Query(min_length=1, max_length=2048, description="Authorization code from Google")
    ],
    redirect_uri: Annotated[
        str,
        Query(
            min_length=1, max_length=2048, description="The redirect URI used in the auth request"
        ),
    ],
    state: Annotated[Optional[str], Query(max_length=256, description="State parameter")] = None,
) -> RedirectResponse:
    """
    Handle OAuth callback redirect from Google (GET request).

    This is a fallback for direct browser redirects.
    The main flow uses the frontend callback page which calls the POST endpoint.
    """
    # Extract frontend origin from redirect_uri (e.g., http://localhost:5173)
    from urllib.parse import urlparse, quote

    parsed = urlparse(redirect_uri)
    frontend_origin = f"{parsed.scheme}://{parsed.netloc}"

    # Redirect to frontend callback page with the code
    # The frontend will then call the POST endpoint
    return RedirectResponse(
        url=f"{frontend_origin}/settings/google-photos/callback?code={quote(code)}&redirect_uri={quote(redirect_uri)}"
    )


@router.post("/google-photos/disconnect")
async def disconnect_google_photos(
    connector_repo: ConnectorRepoDep,
) -> dict:
    """Disconnect from Google Photos and delete tokens."""
    from app.domain.entities.connector import ConnectorType, ConnectorStatus

    # Delete stored tokens
    token_storage = SecureTokenStorage()
    await token_storage.delete_tokens("google_photos_default")

    # Update connector status
    connectors = await connector_repo.find_by_type(ConnectorType.GOOGLE_PHOTOS)
    for connector in connectors:
        connector.status = ConnectorStatus.DISCONNECTED
        await connector_repo.save(connector)

    return {"success": True, "data": {"disconnected": True}}


@router.get("/google-photos/status", response_model=GooglePhotosStatusResponse)
async def get_google_photos_status(
    connector_repo: ConnectorRepoDep,
    photo_repo: PhotoRepoDep,
) -> GooglePhotosStatusResponse:
    """Get the current Google Photos connection status."""
    from app.domain.entities.connector import ConnectorType

    # Check if tokens exist
    token_storage = SecureTokenStorage()
    has_tokens = await token_storage.has_tokens("google_photos_default")

    # Get connector info
    connectors = await connector_repo.find_by_type(ConnectorType.GOOGLE_PHOTOS)
    connector = connectors[0] if connectors else None

    if connector and has_tokens:
        # Count photos indexed for this connector
        photos_indexed = await photo_repo.count_by_connector(connector.id.value)

        return GooglePhotosStatusResponse(
            success=True,
            data={
                "connected": True,
                "connector_id": str(connector.id.value),
                "photos_indexed": photos_indexed,
                "last_sync": connector.last_sync.isoformat() if connector.last_sync else None,
            },
        )

    return GooglePhotosStatusResponse(
        success=True,
        data={
            "connected": False,
            "connector_id": None,
            "photos_indexed": 0,
            "last_sync": None,
        },
    )


# ===================
# Google Photos Picker Sessions
# ===================


@router.post("/{connector_id}/picker/session", response_model=PickerSessionResponse)
async def create_picker_session(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> PickerSessionResponse:
    """
    Create a new photo picker session.

    Returns a pickerUri that the user should open to select photos.
    The frontend should poll the session status until mediaItemsSet is True.
    """
    from app.domain.entities.connector import ConnectorType

    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    if connector.type != ConnectorType.GOOGLE_PHOTOS:
        raise HTTPException(status_code=400, detail="Not a Google Photos connector")

    # Load tokens
    token_storage = SecureTokenStorage()
    tokens = await token_storage.load_tokens(f"google_photos_{connector_id}")

    if not tokens:
        raise HTTPException(status_code=401, detail="Not authenticated - please reconnect")

    # Create picker client and session
    client = GooglePhotosPickerClient(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )

    try:
        session = await client.create_session()

        # Append /autoclose for web to close the picker window automatically
        picker_uri_autoclose = f"{session.picker_uri}/autoclose"

        return PickerSessionResponse(
            success=True,
            data={
                "session_id": session.id,
                "picker_uri": picker_uri_autoclose,
                "poll_interval_seconds": session.poll_interval_seconds,
                "expire_time": session.expire_time.isoformat() if session.expire_time else None,
            },
        )
    finally:
        await client.close()


@router.get(
    "/{connector_id}/picker/session/{session_id}", response_model=PickerSessionStatusResponse
)
async def get_picker_session_status(
    connector_id: UUID,
    session_id: str,
    connector_repo: ConnectorRepoDep,
) -> PickerSessionStatusResponse:
    """
    Get the status of a photo picker session.

    Poll this endpoint to check when the user has finished selecting photos.
    When mediaItemsSet is True, call the import endpoint to import the photos.
    """
    from app.domain.entities.connector import ConnectorType

    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    if connector.type != ConnectorType.GOOGLE_PHOTOS:
        raise HTTPException(status_code=400, detail="Not a Google Photos connector")

    # Load tokens
    token_storage = SecureTokenStorage()
    tokens = await token_storage.load_tokens(f"google_photos_{connector_id}")

    if not tokens:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client = GooglePhotosPickerClient(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )

    try:
        session = await client.get_session(session_id)

        return PickerSessionStatusResponse(
            success=True,
            data={
                "session_id": session.id,
                "media_items_set": session.media_items_set,
                "poll_interval_seconds": session.poll_interval_seconds,
            },
        )
    finally:
        await client.close()


@router.post("/{connector_id}/picker/session/{session_id}/import")
async def import_picker_photos(
    connector_id: UUID,
    session_id: str,
    connector_repo: ConnectorRepoDep,
) -> dict:
    """
    Import photos selected in the picker session.

    This endpoint retrieves the selected photos and queues them for processing.
    Call this after mediaItemsSet is True in the session status.
    """
    from app.domain.entities.connector import ConnectorType

    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    if connector.type != ConnectorType.GOOGLE_PHOTOS:
        raise HTTPException(status_code=400, detail="Not a Google Photos connector")

    # Load tokens
    token_storage = SecureTokenStorage()
    tokens = await token_storage.load_tokens(f"google_photos_{connector_id}")

    if not tokens:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Queue the import task
    from app.adapters.inbound.workers.tasks.google_photos_sync import import_picker_photos_task

    task = import_picker_photos_task.delay(str(connector_id), session_id)

    return {
        "success": True,
        "data": {
            "task_id": task.id,
            "message": "Import started. Photos will be processed in the background.",
        },
    }


@router.delete("/{connector_id}/picker/session/{session_id}")
async def delete_picker_session(
    connector_id: UUID,
    session_id: str,
    connector_repo: ConnectorRepoDep,
) -> dict:
    """
    Delete a picker session.

    Call this after importing photos to clean up the session.
    """
    from app.domain.entities.connector import ConnectorType

    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    if connector.type != ConnectorType.GOOGLE_PHOTOS:
        raise HTTPException(status_code=400, detail="Not a Google Photos connector")

    # Load tokens
    token_storage = SecureTokenStorage()
    tokens = await token_storage.load_tokens(f"google_photos_{connector_id}")

    if not tokens:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client = GooglePhotosPickerClient(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )

    try:
        await client.delete_session(session_id)
        return {"success": True, "data": {"deleted": True}}
    finally:
        await client.close()


# ===================
# Local Folders
# ===================


@router.post(
    "/local",
    response_model=ConnectorResponse,
    status_code=201,
    summary="Create local folder connector",
    description="""
    Create a connector for indexing photos from a local folder.

    Local folder connectors allow the application to import photos from
    directories on the server's filesystem.

    **Security**: Paths are validated against allowed directories configured
    in the server settings to prevent path traversal attacks. Only directories
    within allowed paths can be added.

    Configuration options:
    - **path** (required): Absolute or relative path to the folder
    - **name** (optional): Friendly name (defaults to folder name)
    - **recursive** (default: true): Whether to scan subdirectories
    - **watch** (default: false): Watch for filesystem changes and auto-import
    - **auto_album** (default: false): Automatically create albums based on folder structure

    The connector is created but not immediately synced. Call the sync endpoint
    to start importing photos.
    """,
    responses={
        201: {
            "description": "Connector created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Family Photos",
                            "type": "local",
                            "enabled": True,
                            "status": "connected",
                            "config": {
                                "path": "/photos/family",
                                "recursive": True,
                                "watch": False,
                                "auto_album": False
                            },
                            "last_sync": None,
                            "error_message": None,
                            "created_at": "2024-01-20T10:00:00Z",
                            "updated_at": None
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid request (path doesn't exist, not a directory, etc.)",
            "content": {
                "application/json": {
                    "examples": {
                        "not_exists": {
                            "summary": "Path doesn't exist",
                            "value": {"detail": "Path does not exist: /nonexistent"}
                        },
                        "not_directory": {
                            "summary": "Path is not a directory",
                            "value": {"detail": "Path is not a directory: /file.txt"}
                        }
                    }
                }
            }
        },
        403: {
            "description": "Path not allowed (security restriction)",
            "content": {
                "application/json": {
                    "example": {"detail": "Path not allowed: /etc"}
                }
            }
        },
        409: {
            "description": "Connector already exists for this path",
            "content": {
                "application/json": {
                    "example": {"detail": "Connector already exists for path: /photos"}
                }
            }
        }
    },
    tags=["Connectors"]
)
async def create_local_folder_connector(
    request: LocalFolderCreateRequest,
    connector_repo: ConnectorRepoDep,
) -> ConnectorResponse:
    """Add a local folder for indexing."""
    from pathlib import Path
    from app.domain.entities.connector import Connector
    from app.config import get_settings

    settings = get_settings()

    # Security: Validate path is within allowed directories
    is_allowed, error_msg = settings.is_path_allowed(request.path)
    if not is_allowed:
        raise HTTPException(status_code=403, detail=error_msg or "Path not allowed")

    # Validate path exists
    path = Path(request.path).resolve()
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {request.path}")

    # Validate path is a directory
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")

    # Check for duplicate connector with same path
    existing = await connector_repo.find_by_path(str(path.absolute()))
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Connector already exists for path: {request.path}"
        )

    # Generate default name if not provided
    connector_name = request.name or path.name or "Local Folder"

    # Create connector
    connector = Connector.create_local(
        path=str(path.absolute()),
        name=connector_name,
        recursive=request.recursive if request.recursive is not None else True,
        watch=request.watch if request.watch is not None else False,
        auto_album=request.auto_album if request.auto_album is not None else False,
    )

    # Save connector
    saved = await connector_repo.save(connector)

    return ConnectorResponse(
        success=True,
        data={
            "id": str(saved.id.value),
            "type": saved.type.value,
            "name": saved.name,
            "enabled": saved.enabled,
            "status": saved.status.value,
            "config": saved.config,
            "last_sync": saved.last_sync.isoformat() if saved.last_sync else None,
            "error_message": saved.error_message,
            "created_at": saved.created_at.isoformat(),
            "updated_at": saved.updated_at.isoformat() if saved.updated_at else None,
        },
    )
