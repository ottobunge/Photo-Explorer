"""Folder API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.adapters.inbound.api.schemas.folder_schemas import (
    FolderCreateRequest,
    FolderListResponse,
    FolderResponse,
)
from app.dependencies import ConnectorRepoDep

router = APIRouter()


@router.post("", response_model=FolderResponse, status_code=201)
async def register_folder(
    request: FolderCreateRequest,
    connector_repo: ConnectorRepoDep,
) -> FolderResponse:
    """Register a folder for scanning."""
    # TODO: Implement folder registration logic
    return FolderResponse(
        success=True,
        data={
            "id": "placeholder-uuid",
            "path": request.path,
            "name": request.name,
            "recursive": request.recursive,
            "auto_album": request.auto_album,
            "last_scanned_at": None,
            "created_at": "2024-01-01T00:00:00Z",
        },
    )


@router.get("", response_model=FolderListResponse)
async def list_folders(
    connector_repo: ConnectorRepoDep,
) -> FolderListResponse:
    """List all watched folders."""
    # TODO: Implement folder listing logic
    return FolderListResponse(
        success=True,
        data={"folders": []},
    )


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> FolderResponse:
    """Get a watched folder by ID with stats."""
    # TODO: Implement folder retrieval logic
    raise HTTPException(status_code=404, detail="Folder not found")


@router.post("/{folder_id}/scan")
async def trigger_scan(
    folder_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> dict:
    """Trigger a scan of the folder."""
    # TODO: Implement folder scan logic
    return {"success": True, "data": {"scan_triggered": True}}


@router.delete("/{folder_id}")
async def remove_folder(
    folder_id: UUID,
    connector_repo: ConnectorRepoDep,
    delete_photos: Annotated[bool, Query(description="Also delete indexed photos")] = False,
) -> dict:
    """Remove a watched folder."""
    # TODO: Implement folder removal logic
    return {"success": True, "data": {"deleted": True}}
