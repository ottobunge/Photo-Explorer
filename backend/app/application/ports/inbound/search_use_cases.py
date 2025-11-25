"""Search use cases - Inbound port for search operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

from app.domain.entities import Photo


@dataclass
class SearchFilters:
    """Filters for search queries."""

    # Album filters
    album_ids: Optional[list[UUID]] = None

    # Date filters
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Face filters
    has_faces: Optional[bool] = None
    face_cluster_ids: Optional[list[UUID]] = None
    person_names: Optional[list[str]] = None  # Search by tagged person name

    # Scene filters
    is_indoor: Optional[bool] = None
    scene_types: Optional[list[str]] = None  # Filter by scene type

    # Object filters
    has_objects: Optional[list[str]] = None  # Photos containing these objects

    # Camera/EXIF filters
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    min_width: Optional[int] = None
    min_height: Optional[int] = None

    # Connector filters
    connector_ids: Optional[list[UUID]] = None
    connector_type: Optional[str] = None  # "local", "google_photos"

    # Processing status
    processing_status: Optional[str] = None  # "pending", "processing", "completed"
    has_description: Optional[bool] = None

    # Favorites/Rating (future)
    is_favorite: Optional[bool] = None
    min_rating: Optional[int] = None


@dataclass
class SearchResult:
    """A single search result with score."""

    photo: Photo
    score: float
    highlights: list[str]


@dataclass
class SearchResponse:
    """Search response with results and metadata."""

    results: list[SearchResult]
    total: int
    query_time_ms: float


class SearchUseCases(ABC):
    """Interface defining search-related use cases."""

    @abstractmethod
    async def semantic_search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """
        Perform semantic search using natural language.

        Args:
            query: Natural language search query
            filters: Optional filters to apply
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            SearchResponse with matching photos and scores
        """

    @abstractmethod
    async def find_similar(
        self,
        photo_id: UUID,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Find photos similar to a given photo.

        Args:
            photo_id: The reference photo's ID
            limit: Maximum number of results

        Returns:
            List of similar photos with scores
        """

    @abstractmethod
    async def search_by_face(
        self,
        face_image: bytes,
        limit: int = 20,
    ) -> list[SearchResult]:
        """
        Search for photos containing a similar face.

        Args:
            face_image: Image bytes containing a face to search for
            limit: Maximum number of results

        Returns:
            List of photos containing matching faces
        """
