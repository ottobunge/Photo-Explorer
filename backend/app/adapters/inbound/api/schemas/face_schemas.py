"""Face API schemas."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ClusterNameRequest(BaseModel):
    """Request to name a cluster."""

    name: str = Field(..., min_length=1, max_length=255, description="Cluster name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate cluster name."""
        v = v.strip()
        if not v:
            raise ValueError("Cluster name cannot be empty or whitespace only")
        if len(v) > 255:
            raise ValueError("Cluster name must be at most 255 characters")
        return v


class ClusterMergeRequest(BaseModel):
    """Request to merge clusters."""

    source_cluster_ids: list[UUID] = Field(..., min_length=1, max_length=100, description="Source cluster IDs to merge")
    target_cluster_id: UUID = Field(..., description="Target cluster ID")

    @field_validator("source_cluster_ids")
    @classmethod
    def validate_source_cluster_ids(cls, v: list[UUID]) -> list[UUID]:
        """Validate source cluster IDs."""
        if not v:
            raise ValueError("At least one source cluster ID is required")
        if len(v) > 100:
            raise ValueError("Cannot merge more than 100 clusters at once")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate cluster IDs are not allowed")
        return v

    @field_validator("target_cluster_id")
    @classmethod
    def validate_target_cluster(cls, v: UUID, info) -> UUID:
        """Validate target cluster is not in source clusters."""
        source_ids = info.data.get("source_cluster_ids", [])
        if v in source_ids:
            raise ValueError("Target cluster cannot be in the list of source clusters")
        return v


class FaceMoveRequest(BaseModel):
    """Request to move a face to another cluster."""

    target_cluster_id: UUID = Field(..., description="Target cluster ID")


class RepresentativeFace(BaseModel):
    """Representative face for a cluster."""

    id: str
    crop_url: str


class ClusterData(BaseModel):
    """Face cluster data for API responses."""

    id: str
    name: Optional[str] = None
    face_count: int
    photo_count: int
    representative_face: Optional[RepresentativeFace] = None


class ClusterResponse(BaseModel):
    """Response for single cluster."""

    success: bool
    data: ClusterData
    error: Optional[dict[str, Any]] = None


class ClusterListData(BaseModel):
    """Cluster list response data."""

    clusters: list[ClusterData]


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    per_page: int
    total: int


class ClusterListResponse(BaseModel):
    """Response for cluster list."""

    success: bool
    data: ClusterListData
    meta: PaginationMeta
    error: Optional[dict[str, Any]] = None
