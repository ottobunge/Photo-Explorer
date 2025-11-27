"""Unit tests for FaceRelationship value object."""

from uuid import uuid4

import pytest

from app.domain.value_objects.face_relationship import FaceRelationship


class TestFaceRelationshipCreation:
    """Test FaceRelationship creation and initialization."""

    def test_face_relationship_creation_with_valid_data(self):
        """Test creating FaceRelationship with valid data."""
        person_a_id = uuid4()
        person_b_id = uuid4()
        photo_ids = [uuid4(), uuid4(), uuid4()]

        relationship = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=3,
            sample_photo_ids=photo_ids,
        )

        assert relationship.person_a_id == person_a_id
        assert relationship.person_b_id == person_b_id
        assert relationship.shared_photo_count == 3
        assert relationship.sample_photo_ids == photo_ids

    def test_face_relationship_is_immutable(self):
        """Test that FaceRelationship is immutable (frozen dataclass)."""
        relationship = FaceRelationship(
            person_a_id=uuid4(),
            person_b_id=uuid4(),
            shared_photo_count=5,
            sample_photo_ids=[uuid4()],
        )

        with pytest.raises(AttributeError):
            relationship.shared_photo_count = 10  # Should raise error for frozen dataclass

    def test_face_relationship_with_empty_sample_photos(self):
        """Test creating FaceRelationship with empty sample photo list."""
        relationship = FaceRelationship(
            person_a_id=uuid4(),
            person_b_id=uuid4(),
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        assert relationship.sample_photo_ids == []


class TestFaceRelationshipValidation:
    """Test FaceRelationship validation rules."""

    def test_cannot_create_relationship_with_self(self):
        """Test that a person cannot have a relationship with themselves."""
        person_id = uuid4()

        with pytest.raises(ValueError, match="Cannot create relationship with self"):
            FaceRelationship(
                person_a_id=person_id,
                person_b_id=person_id,
                shared_photo_count=1,
                sample_photo_ids=[],
            )

    def test_cannot_create_relationship_with_zero_photos(self):
        """Test that relationship must have at least one shared photo."""
        with pytest.raises(ValueError, match="Relationship must have at least one shared photo"):
            FaceRelationship(
                person_a_id=uuid4(),
                person_b_id=uuid4(),
                shared_photo_count=0,
                sample_photo_ids=[],
            )

    def test_cannot_create_relationship_with_negative_photo_count(self):
        """Test that shared_photo_count cannot be negative."""
        with pytest.raises(ValueError, match="Relationship must have at least one shared photo"):
            FaceRelationship(
                person_a_id=uuid4(),
                person_b_id=uuid4(),
                shared_photo_count=-1,
                sample_photo_ids=[],
            )


class TestFaceRelationshipComparison:
    """Test FaceRelationship comparison and equality."""

    def test_relationships_are_equal_with_same_data(self):
        """Test that relationships with same data are equal."""
        person_a_id = uuid4()
        person_b_id = uuid4()
        photo_ids = [uuid4(), uuid4()]

        relationship1 = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=2,
            sample_photo_ids=photo_ids,
        )

        relationship2 = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=2,
            sample_photo_ids=photo_ids,
        )

        assert relationship1 == relationship2

    def test_relationships_are_not_equal_with_different_people(self):
        """Test that relationships with different people are not equal."""
        relationship1 = FaceRelationship(
            person_a_id=uuid4(),
            person_b_id=uuid4(),
            shared_photo_count=2,
            sample_photo_ids=[],
        )

        relationship2 = FaceRelationship(
            person_a_id=uuid4(),
            person_b_id=uuid4(),
            shared_photo_count=2,
            sample_photo_ids=[],
        )

        assert relationship1 != relationship2


class TestFaceRelationshipSymmetry:
    """Test that relationships are symmetric (A-B same as B-A)."""

    def test_involves_method_for_person_a(self):
        """Test that involves() returns True for person_a_id."""
        person_a_id = uuid4()
        person_b_id = uuid4()

        relationship = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        assert relationship.involves(person_a_id) is True

    def test_involves_method_for_person_b(self):
        """Test that involves() returns True for person_b_id."""
        person_a_id = uuid4()
        person_b_id = uuid4()

        relationship = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        assert relationship.involves(person_b_id) is True

    def test_involves_method_for_unrelated_person(self):
        """Test that involves() returns False for unrelated person."""
        relationship = FaceRelationship(
            person_a_id=uuid4(),
            person_b_id=uuid4(),
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        unrelated_person_id = uuid4()
        assert relationship.involves(unrelated_person_id) is False

    def test_get_other_person_returns_person_b_when_given_person_a(self):
        """Test get_other_person() returns person_b when given person_a."""
        person_a_id = uuid4()
        person_b_id = uuid4()

        relationship = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        assert relationship.get_other_person(person_a_id) == person_b_id

    def test_get_other_person_returns_person_a_when_given_person_b(self):
        """Test get_other_person() returns person_a when given person_b."""
        person_a_id = uuid4()
        person_b_id = uuid4()

        relationship = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        assert relationship.get_other_person(person_b_id) == person_a_id

    def test_get_other_person_raises_for_unrelated_person(self):
        """Test get_other_person() raises ValueError for unrelated person."""
        relationship = FaceRelationship(
            person_a_id=uuid4(),
            person_b_id=uuid4(),
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        unrelated_person_id = uuid4()
        with pytest.raises(ValueError, match="Person .* is not part of this relationship"):
            relationship.get_other_person(unrelated_person_id)


class TestFaceRelationshipSerialization:
    """Test FaceRelationship serialization."""

    def test_to_dict_serialization(self):
        """Test to_dict serialization."""
        person_a_id = uuid4()
        person_b_id = uuid4()
        photo_ids = [uuid4(), uuid4(), uuid4()]

        relationship = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=3,
            sample_photo_ids=photo_ids,
        )

        result = relationship.to_dict()

        assert result == {
            "person_a_id": str(person_a_id),
            "person_b_id": str(person_b_id),
            "shared_photo_count": 3,
            "sample_photo_ids": [str(pid) for pid in photo_ids],
        }

    def test_to_dict_with_empty_samples(self):
        """Test to_dict serialization with empty sample photos."""
        person_a_id = uuid4()
        person_b_id = uuid4()

        relationship = FaceRelationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            shared_photo_count=1,
            sample_photo_ids=[],
        )

        result = relationship.to_dict()

        assert result == {
            "person_a_id": str(person_a_id),
            "person_b_id": str(person_b_id),
            "shared_photo_count": 1,
            "sample_photo_ids": [],
        }
