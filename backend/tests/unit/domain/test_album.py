"""Unit tests for Album entity."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.entities import Album


class TestAlbumCreation:
    """Tests for Album entity creation."""

    def test_create_album_with_name_only(self):
        """When creating album with name only, it should have correct defaults."""
        album = Album.create(name="Vacation 2023")

        assert album.name == "Vacation 2023"
        assert album.description is None
        assert album.cover_photo_id is None
        assert album.photo_ids == []
        assert album.photo_count == 0
        assert album.created_at is not None
        assert album.updated_at is not None

    def test_create_album_with_description(self):
        """When creating album with description, it should be stored."""
        album = Album.create(
            name="Summer Holidays",
            description="Photos from our summer vacation",
        )

        assert album.name == "Summer Holidays"
        assert album.description == "Photos from our summer vacation"

    def test_created_at_and_updated_at_are_same_on_creation(self):
        """When creating album, created_at and updated_at should be the same."""
        album = Album.create(name="Test Album")

        # Allow small time difference due to execution time
        assert abs((album.created_at - album.updated_at).total_seconds()) < 0.01


class TestAlbumUpdate:
    """Tests for Album update operations."""

    def test_update_name(self):
        """When updating name, it should be changed and updated_at should change."""
        album = Album.create(name="Old Name")
        original_updated_at = album.updated_at

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)

        album.update(name="New Name")

        assert album.name == "New Name"
        assert album.updated_at > original_updated_at

    def test_update_description(self):
        """When updating description, it should be changed."""
        album = Album.create(name="Test Album")

        album.update(description="New description")

        assert album.description == "New description"

    def test_update_both_name_and_description(self):
        """When updating both fields, both should be changed."""
        album = Album.create(name="Old Name", description="Old description")

        album.update(name="New Name", description="New description")

        assert album.name == "New Name"
        assert album.description == "New description"

    def test_update_with_none_values_preserves_current(self):
        """When updating with None, current values should be preserved."""
        album = Album.create(name="Test Album", description="Test description")
        original_name = album.name

        album.update(description="New description")

        assert album.name == original_name
        assert album.description == "New description"


class TestAlbumPhotoOperations:
    """Tests for Album photo management."""

    def test_add_photo(self):
        """When adding photo, it should be in photo_ids."""
        album = Album.create(name="Test Album")
        photo_id = uuid4()

        album.add_photo(photo_id)

        assert photo_id in album.photo_ids
        assert album.photo_count == 1

    def test_add_same_photo_twice_is_idempotent(self):
        """When adding same photo twice, it should only appear once."""
        album = Album.create(name="Test Album")
        photo_id = uuid4()

        album.add_photo(photo_id)
        album.add_photo(photo_id)

        assert album.photo_ids.count(photo_id) == 1
        assert album.photo_count == 1

    def test_add_multiple_photos(self):
        """When adding multiple photos, all should be tracked."""
        album = Album.create(name="Test Album")
        photo_ids = [uuid4() for _ in range(5)]

        for photo_id in photo_ids:
            album.add_photo(photo_id)

        assert album.photo_count == 5
        for photo_id in photo_ids:
            assert photo_id in album.photo_ids

    def test_remove_photo(self):
        """When removing photo, it should not be in photo_ids."""
        album = Album.create(name="Test Album")
        photo_id = uuid4()
        album.add_photo(photo_id)

        album.remove_photo(photo_id)

        assert photo_id not in album.photo_ids
        assert album.photo_count == 0

    def test_remove_photo_not_in_album_is_no_op(self):
        """When removing photo not in album, nothing should change."""
        album = Album.create(name="Test Album")
        photo_id = uuid4()
        album.add_photo(photo_id)
        other_photo_id = uuid4()

        album.remove_photo(other_photo_id)

        assert album.photo_count == 1
        assert photo_id in album.photo_ids

    def test_remove_photo_clears_cover_if_it_was_cover(self):
        """When removing cover photo, cover_photo_id should be None."""
        album = Album.create(name="Test Album")
        photo_id = uuid4()
        album.add_photo(photo_id)
        album.set_cover(photo_id)

        album.remove_photo(photo_id)

        assert album.cover_photo_id is None

    def test_remove_non_cover_photo_preserves_cover(self):
        """When removing non-cover photo, cover should remain."""
        album = Album.create(name="Test Album")
        cover_photo_id = uuid4()
        other_photo_id = uuid4()
        album.add_photo(cover_photo_id)
        album.add_photo(other_photo_id)
        album.set_cover(cover_photo_id)

        album.remove_photo(other_photo_id)

        assert album.cover_photo_id == cover_photo_id


class TestAlbumCoverPhoto:
    """Tests for Album cover photo operations."""

    def test_set_cover(self):
        """When setting cover to album member, it should be set."""
        album = Album.create(name="Test Album")
        photo_id = uuid4()
        album.add_photo(photo_id)

        album.set_cover(photo_id)

        assert album.cover_photo_id == photo_id

    def test_set_cover_non_member_raises_error(self):
        """When setting cover to non-member, it should raise ValueError."""
        album = Album.create(name="Test Album")
        album.add_photo(uuid4())
        non_member_photo_id = uuid4()

        with pytest.raises(ValueError) as exc:
            album.set_cover(non_member_photo_id)

        assert "must be a member of the album" in str(exc.value)

    def test_set_cover_updates_timestamp(self):
        """When setting cover, updated_at should change."""
        album = Album.create(name="Test Album")
        photo_id = uuid4()
        album.add_photo(photo_id)
        original_updated_at = album.updated_at

        import time
        time.sleep(0.01)

        album.set_cover(photo_id)

        assert album.updated_at > original_updated_at


class TestAlbumProperties:
    """Tests for Album computed properties."""

    def test_photo_count_with_empty_album(self):
        """When album is empty, photo_count should be 0."""
        album = Album.create(name="Test Album")

        assert album.photo_count == 0

    def test_photo_count_with_photos(self):
        """When album has photos, photo_count should match."""
        album = Album.create(name="Test Album")
        for _ in range(3):
            album.add_photo(uuid4())

        assert album.photo_count == 3
