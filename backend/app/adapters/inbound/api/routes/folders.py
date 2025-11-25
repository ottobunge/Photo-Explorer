"""Folder API routes.

NOTE: This API is deprecated and superseded by the Connectors API (/api/v1/connectors/local).
Local folder functionality should use the connector endpoints instead:
- POST /api/v1/connectors/local - Create local folder connector
- GET /api/v1/connectors - List all connectors (including local folders)
- GET /api/v1/connectors/{connector_id} - Get connector details
- POST /api/v1/connectors/{connector_id}/sync - Trigger folder scan
- DELETE /api/v1/connectors/{connector_id} - Remove connector

This router is kept for backward compatibility but may be removed in a future version.
"""

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
    """Register a folder for scanning.

    DEPRECATED: Use POST /api/v1/connectors/local instead.
    """
    # GitHub Issue: Implement folder registration or remove deprecated API
    # For now, return a deprecation message
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use POST /api/v1/connectors/local instead.",
    )


@router.get("", response_model=FolderListResponse)
async def list_folders(
    connector_repo: ConnectorRepoDep,
) -> FolderListResponse:
    """List all watched folders.

    DEPRECATED: Use GET /api/v1/connectors instead.
    """
    # GitHub Issue: Implement folder listing or remove deprecated API
    raise HTTPException(
        status_code=410, detail="This endpoint is deprecated. Use GET /api/v1/connectors instead."
    )


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> FolderResponse:
    """Get a watched folder by ID with stats.

    DEPRECATED: Use GET /api/v1/connectors/{connector_id} instead.
    """
    # GitHub Issue: Implement folder retrieval or remove deprecated API
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use GET /api/v1/connectors/{connector_id} instead.",
    )


@router.post("/{folder_id}/scan")
async def trigger_scan(
    folder_id: UUID,
    connector_repo: ConnectorRepoDep,
) -> dict:
    """Trigger a scan of the folder.

    DEPRECATED: Use POST /api/v1/connectors/{connector_id}/sync instead.
    """
    # GitHub Issue: Implement folder scan or remove deprecated API
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use POST /api/v1/connectors/{connector_id}/sync instead.",
    )


@router.delete("/{folder_id}")
async def remove_folder(
    folder_id: UUID,
    connector_repo: ConnectorRepoDep,
    delete_photos: Annotated[bool, Query(description="Also delete indexed photos")] = False,
) -> dict:
    """Remove a watched folder.

    DEPRECATED: Use DELETE /api/v1/connectors/{connector_id} instead.
    """
    # GitHub Issue: Implement folder removal or remove deprecated API
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use DELETE /api/v1/connectors/{connector_id} instead.",
    )
