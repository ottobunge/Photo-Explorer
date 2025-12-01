"""Search service implementing SearchUseCases."""

import logging
import time
from typing import Optional
from uuid import UUID

from app.application.ports.inbound.search_use_cases import (
    SearchFilters,
    SearchResponse,
    SearchResult,
    SearchUseCases,
)
from app.application.ports.outbound import (
    FaceRepository,
    MLServices,
    PhotoRepository,
    VectorStore,
)
from app.domain.entities import Photo

logger = logging.getLogger(__name__)


class SearchService(SearchUseCases):
    """
    Implementation of search use cases.

    Handles semantic search using CLIP embeddings.
    """

    def __init__(
        self,
        photo_repo: PhotoRepository,
        face_repo: FaceRepository,
        vector_store: VectorStore,
        ml_services: MLServices,
    ) -> None:
        self._photo_repo = photo_repo
        self._face_repo = face_repo
        self._vector_store = vector_store
        self._ml_services = ml_services

    async def semantic_search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Perform semantic search using natural language."""
        start_time = time.time()

        # Generate text embedding for query
        query_embedding = await self._ml_services.encode_text(query)

        # Build Qdrant filters
        qdrant_filters = self._build_qdrant_filters(filters) if filters else None

        # Search vector store
        # Note: We fetch more results to handle offset
        search_results = await self._vector_store.search_photos(
            query_embedding=query_embedding,
            limit=limit + offset,
            filters=qdrant_filters,
        )

        # Apply offset
        search_results = search_results[offset:]

        # Fetch full photo entities
        results: list[SearchResult] = []
        for result in search_results:
            photo = await self._photo_repo.find_by_id(result.id)
            if photo:
                # Apply additional filters that can't be done in vector search
                if not self._passes_filters(photo, filters):
                    continue

                results.append(
                    SearchResult(
                        photo=photo,
                        score=result.score,
                        highlights=[query],  # Could extract relevant features
                    )
                )

        query_time_ms = (time.time() - start_time) * 1000

        logger.debug(f"Search '{query}' returned {len(results)} results in {query_time_ms:.1f}ms")

        return SearchResponse(
            results=results[:limit],
            total=len(results),
            query_time_ms=query_time_ms,
        )

    async def find_similar(
        self,
        photo_id: UUID,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Find photos similar to a given photo."""
        # Get the photo's embedding
        embedding = await self._vector_store.get_photo_embedding(photo_id)
        if not embedding:
            return []

        # Search for similar photos
        search_results = await self._vector_store.search_photos(
            query_embedding=embedding,
            limit=limit + 1,  # +1 to exclude the query photo
        )

        # Filter out the query photo and fetch entities
        results: list[SearchResult] = []
        for result in search_results:
            if result.id == photo_id:
                continue

            photo = await self._photo_repo.find_by_id(result.id)
            if photo:
                results.append(
                    SearchResult(
                        photo=photo,
                        score=result.score,
                        highlights=["Similar content"],
                    )
                )

        return results[:limit]

    async def search_by_face(
        self,
        face_image: bytes,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search for photos containing a similar face."""
        # Detect face and get embedding
        detected_faces = await self._ml_services.detect_faces(face_image)
        if not detected_faces:
            return []

        # Use the first detected face's embedding
        face_embedding = detected_faces[0].embedding

        # Search for similar faces
        face_results = await self._vector_store.search_faces(
            query_embedding=face_embedding,
            limit=limit * 2,  # Fetch more since we'll dedupe by photo
        )

        # Get unique photos containing matching faces
        seen_photo_ids: set[UUID] = set()
        results: list[SearchResult] = []

        for result in face_results:
            # Get photo_id from face's metadata
            photo_id_str = result.payload.get("photo_id")
            if not photo_id_str:
                continue

            photo_id = UUID(photo_id_str)
            if photo_id in seen_photo_ids:
                continue

            seen_photo_ids.add(photo_id)

            photo = await self._photo_repo.find_by_id(photo_id)
            if photo:
                results.append(
                    SearchResult(
                        photo=photo,
                        score=result.score,
                        highlights=["Face match"],
                    )
                )

                if len(results) >= limit:
                    break

        return results

    def _build_qdrant_filters(self, filters: SearchFilters) -> dict[str, str | list[str]]:
        """Build Qdrant filter dictionary from SearchFilters."""
        qdrant_filters: dict[str, str | list[str]] = {}

        if filters.album_ids:
            qdrant_filters["album_id"] = [str(aid) for aid in filters.album_ids]

        if filters.connector_ids:
            qdrant_filters["connector_id"] = [str(cid) for cid in filters.connector_ids]

        # Note: Most filters need to be applied post-search since they require
        # database lookups or complex object inspection

        return qdrant_filters

    def _passes_filters(self, photo: Photo, filters: Optional[SearchFilters]) -> bool:
        """Check if a photo passes all filters."""
        if not filters:
            return True

        # Album filter
        if filters.album_ids:
            if not any(aid in photo.album_ids for aid in filters.album_ids):
                return False

        # Date range filter
        if filters.start_date and photo.taken_at:
            if photo.taken_at.date() < filters.start_date:
                return False

        if filters.end_date and photo.taken_at:
            if photo.taken_at.date() > filters.end_date:
                return False

        # Has faces filter
        if filters.has_faces is not None:
            has_faces = len(photo.face_ids) > 0
            if filters.has_faces != has_faces:
                return False

        # Indoor/outdoor filter
        if filters.is_indoor is not None and photo.is_indoor is not None:
            if filters.is_indoor != photo.is_indoor:
                return False

        # Connector filters
        if filters.connector_ids and photo.connector_id:
            if photo.connector_id not in filters.connector_ids:
                return False

        # Processing status
        if filters.processing_status and photo.processing_status:
            if photo.processing_status != filters.processing_status:
                return False

        # Has description filter
        if filters.has_description is not None:
            has_desc = bool(photo.description)
            if filters.has_description != has_desc:
                return False

        return True

    async def search_by_objects(
        self,
        object_labels: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """
        Search for photos containing specific objects.

        Args:
            object_labels: List of object labels to search for
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            SearchResponse with matching photos
        """
        import time

        start_time = time.time()

        # Create a combined search query from object labels
        query = f"photo containing {', '.join(object_labels)}"

        # Use semantic search with object filter
        filters = SearchFilters(has_objects=object_labels)
        response = await self.semantic_search(query, filters, limit, offset)

        return response

    async def search_by_scene(
        self,
        scene_type: str,
        is_indoor: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """
        Search for photos by scene type.

        Args:
            scene_type: Scene type to search for (e.g., "beach", "office")
            is_indoor: Optional indoor/outdoor filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            SearchResponse with matching photos
        """
        import time

        start_time = time.time()

        # Create search query
        query = f"a {scene_type} scene"

        # Use semantic search with scene filters
        filters = SearchFilters(
            scene_types=[scene_type],
            is_indoor=is_indoor,
        )
        response = await self.semantic_search(query, filters, limit, offset)

        return response

    async def search_combined(
        self,
        query: Optional[str] = None,
        filters: Optional[SearchFilters] = None,
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """
        Combined search with optional text query and filters.

        If no query is provided, returns filtered results sorted by date.

        Args:
            query: Optional text query for semantic search
            filters: Optional filters to apply
            sort_by: Sort order ("relevance", "date_asc", "date_desc")
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            SearchResponse with matching photos
        """
        import time

        start_time = time.time()

        if query:
            # Use semantic search
            response = await self.semantic_search(query, filters, limit, offset)
        else:
            # Filter-only search - get photos from repository
            photos = await self._photo_repo.find_all(limit=limit + offset)

            # Apply filters
            filtered = []
            for photo in photos:
                if self._passes_filters(photo, filters):
                    filtered.append(photo)

            # Sort
            if sort_by == "date_desc":
                filtered.sort(key=lambda p: p.taken_at or p.created_at, reverse=True)
            elif sort_by == "date_asc":
                filtered.sort(key=lambda p: p.taken_at or p.created_at)

            # Apply offset and limit
            filtered = filtered[offset : offset + limit]

            # Convert to SearchResults
            results = [SearchResult(photo=photo, score=1.0, highlights=[]) for photo in filtered]

            query_time_ms = (time.time() - start_time) * 1000

            response = SearchResponse(
                results=results,
                total=len(results),
                query_time_ms=query_time_ms,
            )

        return response
