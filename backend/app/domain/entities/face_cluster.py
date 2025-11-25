"""FaceCluster aggregate root entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.domain.exceptions import InvalidOperationException
from app.domain.value_objects import FaceClusterId


@dataclass
class FaceCluster:
    """
    FaceCluster aggregate root.

    Represents a group of faces that belong to the same person.
    Users can name clusters to identify people.
    """

    id: FaceClusterId
    created_at: datetime

    # Optional name (set by user)
    name: Optional[str] = None

    # Representative face for display
    representative_face_id: Optional[UUID] = None

    # Member faces (IDs only)
    face_ids: list[UUID] = field(default_factory=list)

    updated_at: Optional[datetime] = None

    @classmethod
    def create(cls, initial_face_id: Optional[UUID] = None) -> "FaceCluster":
        """Factory method to create a new cluster."""
        now = datetime.utcnow()
        face_ids = [initial_face_id] if initial_face_id else []
        return cls(
            id=FaceClusterId(uuid4()),
            created_at=now,
            updated_at=now,
            face_ids=face_ids,
            representative_face_id=initial_face_id,
        )

    def set_name(self, name: str) -> None:
        """Set or update the name for this cluster (person's name)."""
        self.name = name.strip()
        self._touch()

    def clear_name(self) -> None:
        """Remove the name from this cluster."""
        self.name = None
        self._touch()

    def add_face(self, face_id: UUID) -> None:
        """Add a face to this cluster."""
        if face_id not in self.face_ids:
            self.face_ids.append(face_id)
            # Set as representative if this is the first face
            if self.representative_face_id is None:
                self.representative_face_id = face_id
            self._touch()

    def remove_face(self, face_id: UUID) -> None:
        """Remove a face from this cluster."""
        if face_id in self.face_ids:
            self.face_ids.remove(face_id)
            # Update representative if needed
            if self.representative_face_id == face_id:
                self.representative_face_id = self.face_ids[0] if self.face_ids else None
            self._touch()

    def set_representative(self, face_id: UUID) -> None:
        """Set the representative face for display."""
        if face_id not in self.face_ids:
            raise InvalidOperationException(f"Face {face_id} is not a member of this cluster")
        self.representative_face_id = face_id
        self._touch()

    def merge_from(self, other: "FaceCluster") -> list[UUID]:
        """
        Merge another cluster into this one.

        Returns the list of face IDs that were moved.
        """
        moved_faces = []
        for face_id in other.face_ids:
            if face_id not in self.face_ids:
                self.face_ids.append(face_id)
                moved_faces.append(face_id)

        # Keep this cluster's name if it has one, otherwise use other's
        if not self.name and other.name:
            self.name = other.name

        self._touch()
        return moved_faces

    @property
    def face_count(self) -> int:
        """Get the number of faces in this cluster."""
        return len(self.face_ids)

    @property
    def is_named(self) -> bool:
        """Check if this cluster has been named."""
        return self.name is not None and len(self.name) > 0

    @property
    def is_empty(self) -> bool:
        """Check if this cluster has no faces."""
        return len(self.face_ids) == 0

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
