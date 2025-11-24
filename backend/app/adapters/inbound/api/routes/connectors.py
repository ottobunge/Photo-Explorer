"""Connectors API routes."""

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
            "thumbnail_url": f"/api/v1/photos/{photo.id.value}/thumbnail" if photo.thumbnail_path or photo.is_remote else None,
            "taken_at": photo.taken_at.isoformat() if photo.taken_at else None,
            "processing_status": photo.processing_status,
            "created_at": photo.created_at.isoformat(),
        }
        for photo in photos
    ]

    return {
        "success": True,
        "data": {"photos": photo_list},
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.patch("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: UUID,
    request: ConnectorUpdateRequest,
    connector_repo: ConnectorRepoDep,
) -> ConnectorResponse:
    """Update a connector's configuration."""
    # TODO: Implement connector update logic
    raise HTTPException(status_code=404, detail="Connector not found")


@router.delete("/{connector_id}")
async def delete_connector(
    connector_id: UUID,
    connector_repo: ConnectorRepoDep,
    delete_photos: Annotated[bool, Query(description="Also delete indexed photos")] = False,
) -> dict:
    """Delete a connector."""
    from app.domain.entities.connector import ConnectorType

    connector = await connector_repo.find_by_id(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Delete associated tokens if it's a Google Photos connector
    if connector.type == ConnectorType.GOOGLE_PHOTOS:
        token_storage = SecureTokenStorage()
        await token_storage.delete_tokens(f"google_photos_{connector_id}")

    # TODO: If delete_photos is True, delete associated photos

    deleted = await connector_repo.delete(connector_id)
    return {"success": True, "data": {"deleted": deleted}}


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
    redirect_uri: Annotated[str, Query(min_length=1, max_length=2048, description="OAuth callback URL")],
    state: Annotated[Optional[str], Query(max_length=256, description="State parameter for CSRF protection")] = None,
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

        return {
            "success": True,
            "data": {
                "connected": True,
                "connector_id": str(connector.id.value),
                "expires_at": tokens.expires_at.isoformat(),
            },
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {str(e)}")
    finally:
        await client.close()


@router.get("/google-photos/callback")
async def google_photos_oauth_callback_redirect(
    code: Annotated[str, Query(min_length=1, max_length=2048, description="Authorization code from Google")],
    redirect_uri: Annotated[str, Query(min_length=1, max_length=2048, description="The redirect URI used in the auth request")],
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
        return GooglePhotosStatusResponse(
            success=True,
            data={
                "connected": True,
                "connector_id": str(connector.id.value),
                "photos_indexed": 0,  # TODO: count from photo_repo
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


@router.get("/{connector_id}/picker/session/{session_id}", response_model=PickerSessionStatusResponse)
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


@router.post("/local", response_model=ConnectorResponse, status_code=201)
async def create_local_folder_connector(
    request: LocalFolderCreateRequest,
    connector_repo: ConnectorRepoDep,
) -> ConnectorResponse:
    """Add a local folder for indexing."""
    # TODO: Implement local folder connector creation logic
    return ConnectorResponse(
        success=True,
        data={
            "id": "placeholder-uuid",
            "type": "local",
            "name": request.name or request.path,
            "enabled": True,
            "status": "connected",
            "config": {
                "path": request.path,
                "recursive": request.recursive,
                "watch": request.watch,
                "auto_album": request.auto_album,
            },
            "last_sync": None,
            "created_at": "2024-01-01T00:00:00Z",
        },
    )
