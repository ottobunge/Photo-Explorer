"""FaceRelationship value object - Relationship between two people based on photo co-appearances."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class FaceRelationship:
    """
    Immutable relationship between two people based on shared photos.

    Represents a symmetric relationship where two people appear together
    in one or more photos.
    """

    person_a_id: UUID
    person_b_id: UUID
    shared_photo_count: int
    sample_photo_ids: list[UUID]

    def __post_init__(self) -> None:
        """Validate relationship constraints."""
        if self.person_a_id == self.person_b_id:
            raise ValueError("Cannot create relationship with self")

        if self.shared_photo_count <= 0:
            raise ValueError("Relationship must have at least one shared photo")

    def involves(self, person_id: UUID) -> bool:
        """
        Check if a person is part of this relationship.

        Args:
            person_id: The person ID to check.

        Returns:
            bool: True if person is either person_a or person_b.
        """
        return person_id in (self.person_a_id, self.person_b_id)

    def get_other_person(self, person_id: UUID) -> UUID:
        """
        Get the other person in the relationship.

        Given one person in the relationship, returns the other person.

        Args:
            person_id: ID of one person in the relationship.

        Returns:
            UUID: ID of the other person in the relationship.

        Raises:
            ValueError: If person_id is not part of this relationship.
        """
        if person_id == self.person_a_id:
            return self.person_b_id
        elif person_id == self.person_b_id:
            return self.person_a_id
        else:
            raise ValueError(f"Person {person_id} is not part of this relationship")

    def to_dict(self) -> dict[str, object]:
        """
        Serialize FaceRelationship to a dictionary.

        Returns:
            dict: Dictionary representation with all fields.
                  UUID objects are serialized to strings.
        """
        return {
            "person_a_id": str(self.person_a_id),
            "person_b_id": str(self.person_b_id),
            "shared_photo_count": self.shared_photo_count,
            "sample_photo_ids": [str(pid) for pid in self.sample_photo_ids],
        }
