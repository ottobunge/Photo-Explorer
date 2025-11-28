"""Search API schemas."""

import re
from datetime import date, timedelta
from typing import Any, Optional, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ErrorDetails(TypedDict, total=False):
    """Error response details."""

    code: str
    message: str
    details: dict[str, Any]  # type: ignore[explicit-any]


class SearchFilters(BaseModel):  # type: ignore[explicit-any]
    """Filters for search queries."""

    album_ids: Optional[list[UUID]] = Field(None, max_length=100, description="Filter by album IDs")
    connector_ids: Optional[list[UUID]] = Field(
        None, max_length=50, description="Filter by connector IDs"
    )
    start_date: Optional[date] = Field(None, description="Filter photos taken after this date")
    end_date: Optional[date] = Field(None, description="Filter photos taken before this date")
    has_faces: Optional[bool] = Field(None, description="Filter by presence of faces")
    face_cluster_ids: Optional[list[UUID]] = Field(
        None, max_length=100, description="Filter by face cluster IDs"
    )
    is_indoor: Optional[bool] = Field(None, description="Filter by indoor/outdoor classification")

    @field_validator("album_ids")
    @classmethod
    def validate_album_ids(cls, v: Optional[list[UUID]]) -> Optional[list[UUID]]:
        """Validate album IDs list."""
        if v is not None:
            if len(v) > 100:
                raise ValueError("Cannot filter by more than 100 albums at once")
            if len(v) != len(set(v)):
                raise ValueError("Duplicate album IDs are not allowed")
        return v

    @field_validator("connector_ids")
    @classmethod
    def validate_connector_ids(cls, v: Optional[list[UUID]]) -> Optional[list[UUID]]:
        """Validate connector IDs list."""
        if v is not None:
            if len(v) > 50:
                raise ValueError("Cannot filter by more than 50 connectors at once")
            if len(v) != len(set(v)):
                raise ValueError("Duplicate connector IDs are not allowed")
        return v

    @field_validator("face_cluster_ids")
    @classmethod
    def validate_face_cluster_ids(cls, v: Optional[list[UUID]]) -> Optional[list[UUID]]:
        """Validate face cluster IDs list."""
        if v is not None:
            if len(v) > 100:
                raise ValueError("Cannot filter by more than 100 face clusters at once")
            if len(v) != len(set(v)):
                raise ValueError("Duplicate face cluster IDs are not allowed")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(
        cls, v: Optional[date], info: Any  # type: ignore[explicit-any]
    ) -> Optional[date]:
        """Validate date range is logical."""
        if v is not None:
            # Check if end_date is in the future
            if v > date.today() + timedelta(days=1):
                raise ValueError("End date cannot be more than 1 day in the future")
            # Check if date range is logical
            start_date = info.data.get("start_date")
            if start_date is not None and v < start_date:
                raise ValueError("End date must be after or equal to start date")
        return v


class SearchRequest(BaseModel):  # type: ignore[explicit-any]
    """Request for semantic search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language search query",
        example="sunset over mountains",
    )
    filters: Optional[SearchFilters] = Field(None, description="Optional filters to narrow results")
    limit: int = Field(
        20, ge=1, le=100, description="Maximum number of results to return", example=20
    )
    offset: int = Field(
        0, ge=0, le=10000, description="Number of results to skip for pagination", example=0
    )
    similarity_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score (0.0-1.0). Only return results with score >= threshold.",
        example=0.8,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "sunset over mountains",
                "filters": {
                    "connector_ids": ["650e8400-e29b-41d4-a716-446655440000"],
                    "start_date": "2024-01-01",
                    "is_indoor": False,
                },
                "limit": 20,
                "offset": 0,
            }
        }

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        v = v.strip()
        if not v:
            raise ValueError("Search query cannot be empty or whitespace only")
        if len(v) > 500:
            raise ValueError("Search query must be at most 500 characters")
        # Check for potential SQL injection patterns (defense in depth)
        suspicious_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bDROP\b.*\bTABLE\b)",
            r"(\bDELETE\b.*\bFROM\b)",
            r"(--|;|\/\*|\*\/|xp_|sp_)",
            r"(\bOR\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",  # OR '1'='1' tautologies
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Search query contains suspicious patterns")
        return v


class SearchResultItem(BaseModel):  # type: ignore[explicit-any]
    """Single search result."""

    photo: dict[str, Any] = Field(..., description="Photo metadata")  # type: ignore[explicit-any]
    score: float = Field(
        ..., description="Similarity score (0-1, higher is better)", ge=0, le=1, example=0.85
    )
    highlights: list[str] = Field(
        ..., description="Matched keywords or phrases", example=["mountain", "sunset"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "photo": {
                    "id": "650e8400-e29b-41d4-a716-446655440001",
                    "filename": "IMG_1234.jpg",
                    "thumbnail_url": "/api/v1/photos/650e8400-e29b-41d4-a716-446655440001/thumbnail",
                    "taken_at": "2024-01-15T14:30:00Z",
                    "description": "Mountain sunset",
                },
                "score": 0.85,
                "highlights": ["mountain", "sunset"],
            }
        }


class SearchResultData(BaseModel):  # type: ignore[explicit-any]
    """Search results data."""

    results: list[SearchResultItem] = Field(..., description="List of matching photos")
    query_embedding_time_ms: float = Field(
        ..., description="Time to generate query embedding (ms)", example=45.2
    )
    search_time_ms: float = Field(
        ..., description="Time to search vector database (ms)", example=12.8
    )

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "photo": {
                            "id": "650e8400-e29b-41d4-a716-446655440001",
                            "filename": "IMG_1234.jpg",
                            "thumbnail_url": "/api/v1/photos/650e8400-e29b-41d4-a716-446655440001/thumbnail",
                        },
                        "score": 0.85,
                        "highlights": [],
                    }
                ],
                "query_embedding_time_ms": 45.2,
                "search_time_ms": 12.8,
            }
        }


class SearchMeta(BaseModel):  # type: ignore[explicit-any]
    """Search metadata."""

    total: int = Field(..., description="Total number of results", ge=0, example=5)
    limit: int = Field(..., description="Maximum results requested", ge=1, example=20)
    offset: int = Field(..., description="Number of results skipped", ge=0, example=0)

    class Config:
        json_schema_extra = {
            "example": {
                "total": 5,
                "limit": 20,
                "offset": 0,
            }
        }


class SearchResponse(BaseModel):  # type: ignore[explicit-any]
    """Response for search."""

    success: bool = Field(..., description="Whether the search succeeded", example=True)
    data: SearchResultData
    meta: SearchMeta
    error: Optional[ErrorDetails] = Field(None, description="Error details if success is false")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "results": [
                        {
                            "photo": {
                                "id": "650e8400-e29b-41d4-a716-446655440001",
                                "filename": "IMG_1234.jpg",
                                "thumbnail_url": "/api/v1/photos/650e8400-e29b-41d4-a716-446655440001/thumbnail",
                                "description": "Mountain sunset landscape",
                            },
                            "score": 0.85,
                            "highlights": [],
                        }
                    ],
                    "query_embedding_time_ms": 45.2,
                    "search_time_ms": 12.8,
                },
                "meta": {
                    "total": 5,
                    "limit": 20,
                    "offset": 0,
                },
            }
        }
