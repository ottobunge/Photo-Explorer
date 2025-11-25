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


@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic photo search",
    description="""
    Search photos using natural language queries powered by AI.

    This endpoint uses CLIP (Contrastive Language-Image Pre-training) to understand
    your search query and find photos that match the semantic meaning, not just
    keywords or tags.

    **How it works:**
    1. Your text query is converted to a vector embedding using CLIP
    2. The embedding is compared against all photo embeddings in the vector database (Qdrant)
    3. Photos are ranked by semantic similarity score
    4. Results can be filtered by connector or album

    **Example queries:**
    - "sunset over the ocean"
    - "people smiling at a party"
    - "mountain landscape with snow"
    - "cat sleeping on a couch"
    - "birthday cake with candles"

    **Features:**
    - Understands concepts, not just keywords
    - Works across languages
    - Finds visually similar content
    - Supports pagination with offset/limit
    - Optional filtering by connector or album

    **Performance:**
    The response includes timing information:
    - query_embedding_time_ms: Time to convert text to embedding
    - search_time_ms: Time to search the vector database

    **Note:** Only photos that have been processed (have embeddings) will appear
    in search results. Check processing_status in photo metadata.
    """,
    responses={
        200: {
            "description": "Search results with timing information",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "results": [
                                {
                                    "photo": {
                                        "id": "550e8400-e29b-41d4-a716-446655440000",
                                        "filename": "IMG_1234.jpg",
                                        "thumbnail_url": "/api/v1/photos/550e8400-e29b-41d4-a716-446655440000/thumbnail",
                                        "taken_at": "2024-01-15T14:30:00Z",
                                        "description": "A beautiful sunset over the ocean",
                                        "connector_type": "google_photos"
                                    },
                                    "score": 0.89,
                                    "highlights": []
                                }
                            ],
                            "query_embedding_time_ms": 45.2,
                            "search_time_ms": 12.8
                        },
                        "meta": {
                            "total": 25,
                            "limit": 20,
                            "offset": 0
                        }
                    }
                }
            }
        },
        500: {
            "description": "Search failed (ML service unavailable, etc.)",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": {
                            "results": [],
                            "query_embedding_time_ms": 0,
                            "search_time_ms": 0
                        },
                        "meta": {"total": 0, "limit": 20, "offset": 0},
                        "error": {"message": "ML service unavailable"}
                    }
                }
            }
        }
    },
    tags=["Search"]
)
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


@router.get(
    "",
    summary="Semantic search (GET)",
    description="""
    Search photos using natural language queries - GET version for easy browser testing.

    This is a convenience endpoint that provides the same semantic search functionality
    as the POST endpoint, but using query parameters instead of a request body.

    **Use this endpoint for:**
    - Quick testing in a browser
    - Simple URL-based searches
    - Direct linking to search results

    **For production use**, prefer the POST endpoint which:
    - Supports more complex filter combinations
    - Handles special characters better
    - Follows REST conventions

    See the POST /search endpoint documentation for detailed information about
    how semantic search works, example queries, and performance characteristics.
    """,
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "results": [
                                {
                                    "photo": {
                                        "id": "550e8400-e29b-41d4-a716-446655440000",
                                        "filename": "IMG_1234.jpg",
                                        "thumbnail_url": "/api/v1/photos/550e8400-e29b-41d4-a716-446655440000/thumbnail"
                                    },
                                    "score": 0.89
                                }
                            ],
                            "query_embedding_time_ms": 45.2,
                            "search_time_ms": 12.8
                        },
                        "meta": {"total": 25, "limit": 20, "offset": 0}
                    }
                }
            }
        },
        400: {
            "description": "Invalid query parameters",
            "content": {
                "application/json": {
                    "example": {"detail": "Query string is required"}
                }
            }
        }
    },
    tags=["Search"]
)
async def search_photos_get(
    q: Annotated[str, Query(min_length=1, max_length=500, description="Search query text")],
    ml_services: MLServicesDep,
    vector_store: VectorStoreDep,
    photo_repo: PhotoRepoDep,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results (1-100)")] = 20,
    offset: Annotated[int, Query(ge=0, le=10000, description="Results to skip")] = 0,
    connector_id: Annotated[Optional[str], Query(description="Filter by connector ID (UUID)")] = None,
    album_id: Annotated[Optional[str], Query(description="Filter by album ID (UUID)")] = None,
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
