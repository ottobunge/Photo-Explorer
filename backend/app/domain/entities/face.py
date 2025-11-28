"""Face entity."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.domain.value_objects import BoundingBox, FaceId


@dataclass
class Face:
    """
    Face entity.

    Represents a detected face within a photo.
    Belongs to both a Photo and a FaceCluster.
    """

    id: FaceId
    photo_id: UUID
    bbox: BoundingBox
    created_at: datetime

    # Cluster association
    cluster_id: Optional[UUID] = None

    # Face crop storage
    crop_path: Optional[str] = None

    # Quality metrics
    quality_score: Optional[float] = None
    detection_confidence: Optional[float] = None

    @classmethod
    def create(
        cls,
        photo_id: UUID,
        bbox: BoundingBox,
        quality_score: Optional[float] = None,
        detection_confidence: Optional[float] = None,
    ) -> "Face":
        """Factory method to create a new face."""
        return cls(
            id=FaceId(uuid4()),
            photo_id=photo_id,
            bbox=bbox,
            quality_score=quality_score,
            detection_confidence=detection_confidence,
            created_at=datetime.now(timezone.utc),
        )

    def assign_to_cluster(self, cluster_id: UUID) -> None:
        """Assign this face to a cluster."""
        self.cluster_id = cluster_id

    def remove_from_cluster(self) -> None:
        """Remove this face from its current cluster."""
        self.cluster_id = None

    def set_crop_path(self, path: str) -> None:
        """Set the path to the cropped face image."""
        self.crop_path = path

    @property
    def is_clustered(self) -> bool:
        """Check if this face belongs to a cluster."""
        return self.cluster_id is not None

    @property
    def has_crop(self) -> bool:
        """Check if a cropped image exists for this face."""
        return self.crop_path is not None
