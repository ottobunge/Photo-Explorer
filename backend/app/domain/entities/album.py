"""Album aggregate root entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.domain.value_objects import AlbumId


@dataclass
class Album:
    """
    Album aggregate root.

    Represents a collection of photos organized by the user.
    """

    id: AlbumId
    name: str
    created_at: datetime

    # Optional fields
    description: Optional[str] = None
    cover_photo_id: Optional[UUID] = None
    updated_at: Optional[datetime] = None

    # Photo associations (IDs only)
    photo_ids: list[UUID] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, description: Optional[str] = None) -> "Album":
        """Factory method to create a new album."""
        now = datetime.now(timezone.utc)
        return cls(
            id=AlbumId(uuid4()),
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )

    def update(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Update album details."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self._touch()

    def add_photo(self, photo_id: UUID) -> None:
        """Add a photo to this album."""
        if photo_id not in self.photo_ids:
            self.photo_ids.append(photo_id)
            self._touch()

    def remove_photo(self, photo_id: UUID) -> None:
        """Remove a photo from this album."""
        if photo_id in self.photo_ids:
            self.photo_ids.remove(photo_id)
            # Clear cover if it was the removed photo
            if self.cover_photo_id == photo_id:
                self.cover_photo_id = None
            self._touch()

    def set_cover(self, photo_id: UUID) -> None:
        """Set the cover photo for this album."""
        if photo_id not in self.photo_ids:
            raise ValueError("Cover photo must be a member of the album")
        self.cover_photo_id = photo_id
        self._touch()

    @property
    def photo_count(self) -> int:
        """Get the number of photos in this album."""
        return len(self.photo_ids)

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)
