"""Search API routes."""

import logging
import time
from typing import Annotated, Optional

from fastapi import APIRouter, Query

from app.adapters.inbound.api.schemas.search_schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.dependencies import MLServicesDep, PhotoRepoDep, VectorStoreDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    ml_services: MLServicesDep,
    vector_store: VectorStoreDep,
    photo_repo: PhotoRepoDep,
) -> SearchResponse:
    """
    Perform semantic search using natural language.

    The query text is converted to a CLIP embedding and used
    to find visually and semantically similar photos.
    """
    try:
        # Generate text embedding
        start_embed = time.time()
        query_embedding = await ml_services.encode_text(request.query)
        embed_time_ms = (time.time() - start_embed) * 1000

        # Search in Qdrant
        start_search = time.time()
        search_results = await vector_store.search_photos(
            query_embedding=query_embedding,
            limit=request.limit + request.offset,  # Get enough for offset
        )
        search_time_ms = (time.time() - start_search) * 1000

        # Apply offset
        search_results = search_results[request.offset:]

        # Get connector filter from request
        connector_ids = None
        album_ids = None
        if request.filters:
            connector_ids = request.filters.connector_ids
            album_ids = request.filters.album_ids

        # Fetch full photo details from database
        results: list[SearchResultItem] = []
        for result in search_results:
            photo = await photo_repo.find_by_id(result.id)
            if photo:
                # Apply connector filter
                if connector_ids and photo.connector_id not in connector_ids:
                    continue

                # Apply album filter
                if album_ids:
                    photo_album_ids = set(photo.album_ids)
                    if not photo_album_ids.intersection(album_ids):
                        continue

                results.append(SearchResultItem(
                    photo={
                        "id": str(photo.id.value),
                        "filename": photo.filename,
                        "thumbnail_url": f"/api/v1/photos/{photo.id.value}/thumbnail" if photo.thumbnail_path or photo.is_remote else None,
                        "mime_type": photo.mime_type,
                        "width": photo.width,
                        "height": photo.height,
                        "taken_at": photo.taken_at.isoformat() if photo.taken_at else None,
                        "connector_type": photo.connector_type,
                        "connector_id": str(photo.connector_id) if photo.connector_id else None,
                        "description": photo.description,
                    },
                    score=result.score,
                    highlights=[],  # Could add matched keywords later
                ))

        return SearchResponse(
            success=True,
            data={
                "results": results,
                "query_embedding_time_ms": embed_time_ms,
                "search_time_ms": search_time_ms,
            },
            meta={
                "total": len(results),
                "limit": request.limit,
                "offset": request.offset,
            },
        )

    except Exception as e:
        logger.exception(f"Search failed: {e}")
        return SearchResponse(
            success=False,
            data={
                "results": [],
                "query_embedding_time_ms": 0,
                "search_time_ms": 0,
            },
            meta={
                "total": 0,
                "limit": request.limit,
                "offset": request.offset,
            },
            error={"message": str(e)},
        )


@router.get("")
async def search_photos_get(
    q: Annotated[str, Query(min_length=1, max_length=500, description="Search query")],
    ml_services: MLServicesDep,
    vector_store: VectorStoreDep,
    photo_repo: PhotoRepoDep,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results (1-100)")] = 20,
    offset: Annotated[int, Query(ge=0, le=10000, description="Results to skip")] = 0,
    connector_id: Annotated[Optional[str], Query(description="Filter by connector ID")] = None,
    album_id: Annotated[Optional[str], Query(description="Filter by album ID")] = None,
) -> SearchResponse:
    """
    GET endpoint for semantic search (convenience for browser testing).
    """
    from uuid import UUID
    from app.adapters.inbound.api.schemas.search_schemas import SearchFilters

    filters = None
    if connector_id or album_id:
        filters = SearchFilters(
            connector_ids=[UUID(connector_id)] if connector_id else None,
            album_ids=[UUID(album_id)] if album_id else None,
        )

    request = SearchRequest(query=q, limit=limit, offset=offset, filters=filters)
    return await semantic_search(request, ml_services, vector_store, photo_repo)
