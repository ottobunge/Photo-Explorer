"""Unit tests for Photo entity."""

from uuid import uuid4

import pytest

from app.domain.entities import Photo
from app.domain.value_objects import SceneClassification


class TestPhotoCreation:
    """Tests for Photo entity creation."""

    def test_create_photo_with_minimal_data(self):
        """When creating a photo with minimal data, it should have correct defaults."""
        photo = Photo.create(
            filename="beach.jpg",
            storage_path="/storage/abc123.jpg",
        )

        assert photo.filename == "beach.jpg"
        assert photo.storage_path == "/storage/abc123.jpg"
        assert photo.processing_status == "pending"
        assert photo.album_ids == []
        assert photo.face_ids == []
        assert photo.created_at is not None

    def test_create_photo_with_album(self):
        """When creating a photo with an album, it should be associated."""
        album_id = uuid4()
        photo = Photo.create(
            filename="mountain.jpg",
            storage_path="/storage/def456.jpg",
            album_id=album_id,
        )

        assert album_id in photo.album_ids

    def test_create_photo_with_original_path(self):
        """When creating a photo from filesystem, original path should be stored."""
        photo = Photo.create(
            filename="vacation.jpg",
            storage_path="/storage/ghi789.jpg",
            original_path="/home/user/Pictures/vacation.jpg",
        )

        assert photo.original_path == "/home/user/Pictures/vacation.jpg"


class TestPhotoAlbumOperations:
    """Tests for Photo album associations."""

    def test_add_to_album(self):
        """When adding photo to album, it should be in album_ids."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")
        album_id = uuid4()

        photo.add_to_album(album_id)

        assert album_id in photo.album_ids

    def test_add_to_same_album_twice_is_idempotent(self):
        """When adding to same album twice, it should only appear once."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")
        album_id = uuid4()

        photo.add_to_album(album_id)
        photo.add_to_album(album_id)

        assert photo.album_ids.count(album_id) == 1

    def test_remove_from_album(self):
        """When removing from album, it should not be in album_ids."""
        album_id = uuid4()
        photo = Photo.create(
            filename="test.jpg",
            storage_path="/storage/test.jpg",
            album_id=album_id,
        )

        photo.remove_from_album(album_id)

        assert album_id not in photo.album_ids


class TestPhotoProcessing:
    """Tests for Photo processing status."""

    def test_set_valid_processing_status(self):
        """When setting valid status, it should be updated."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")

        photo.set_processing_status("processing")
        assert photo.processing_status == "processing"

        photo.set_processing_status("completed")
        assert photo.processing_status == "completed"

    def test_set_invalid_processing_status_raises_error(self):
        """When setting invalid status, it should raise ValueError."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")

        with pytest.raises(ValueError) as exc:
            photo.set_processing_status("invalid")

        assert "Invalid status" in str(exc.value)

    def test_is_processed_when_completed(self):
        """When status is completed, is_processed should be True."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")
        photo.set_processing_status("completed")

        assert photo.is_processed is True

    def test_is_processed_when_pending(self):
        """When status is pending, is_processed should be False."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")

        assert photo.is_processed is False


class TestPhotoAiAnalysis:
    """Tests for Photo AI-generated content."""

    def test_set_ai_analysis(self):
        """When setting AI analysis, all fields should be updated."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")
        scene = SceneClassification.outdoor("beach", confidence=0.95)

        photo.set_ai_analysis(
            description="A sunny beach with palm trees",
            scene_classification=scene,
            detected_objects=["palm tree", "ocean", "sand"],
        )

        assert photo.description == "A sunny beach with palm trees"
        assert photo.scene_classification == scene
        assert "palm tree" in photo.detected_objects
        assert photo.is_indoor is False

    def test_is_indoor_with_indoor_scene(self):
        """When scene is indoor, is_indoor should be True."""
        photo = Photo.create(filename="test.jpg", storage_path="/storage/test.jpg")
        scene = SceneClassification.indoor("office")

        photo.set_ai_analysis(scene_classification=scene)

        assert photo.is_indoor is True
