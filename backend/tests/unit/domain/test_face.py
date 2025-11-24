"""Unit tests for Face entity."""

from uuid import uuid4

import pytest

from app.domain.entities import Face
from app.domain.value_objects import BoundingBox


class TestFaceCreation:
    """Tests for Face entity creation."""

    def test_create_face_with_minimal_data(self):
        """When creating face with minimal data, it should have correct defaults."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)

        face = Face.create(photo_id=photo_id, bbox=bbox)

        assert face.photo_id == photo_id
        assert face.bbox == bbox
        assert face.cluster_id is None
        assert face.crop_path is None
        assert face.quality_score is None
        assert face.detection_confidence is None
        assert face.created_at is not None
        assert face.is_clustered is False
        assert face.has_crop is False

    def test_create_face_with_quality_metrics(self):
        """When creating face with quality metrics, they should be stored."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)

        face = Face.create(
            photo_id=photo_id,
            bbox=bbox,
            quality_score=0.95,
            detection_confidence=0.98,
        )

        assert face.quality_score == 0.95
        assert face.detection_confidence == 0.98


class TestFaceClusterOperations:
    """Tests for Face cluster assignment."""

    def test_assign_to_cluster(self):
        """When assigning to cluster, cluster_id should be set."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)
        cluster_id = uuid4()

        face.assign_to_cluster(cluster_id)

        assert face.cluster_id == cluster_id
        assert face.is_clustered is True

    def test_remove_from_cluster(self):
        """When removing from cluster, cluster_id should be None."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)
        cluster_id = uuid4()
        face.assign_to_cluster(cluster_id)

        face.remove_from_cluster()

        assert face.cluster_id is None
        assert face.is_clustered is False

    def test_reassign_to_different_cluster(self):
        """When reassigning to different cluster, cluster_id should update."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)
        cluster1_id = uuid4()
        cluster2_id = uuid4()

        face.assign_to_cluster(cluster1_id)
        face.assign_to_cluster(cluster2_id)

        assert face.cluster_id == cluster2_id


class TestFaceCropOperations:
    """Tests for Face crop path operations."""

    def test_set_crop_path(self):
        """When setting crop path, it should be stored."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)

        face.set_crop_path("/storage/crops/face123.jpg")

        assert face.crop_path == "/storage/crops/face123.jpg"
        assert face.has_crop is True

    def test_update_crop_path(self):
        """When updating crop path, it should be overwritten."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)
        face.set_crop_path("/storage/crops/old.jpg")

        face.set_crop_path("/storage/crops/new.jpg")

        assert face.crop_path == "/storage/crops/new.jpg"


class TestFaceProperties:
    """Tests for Face computed properties."""

    def test_is_clustered_when_assigned(self):
        """When face is assigned to cluster, is_clustered should be True."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)
        face.assign_to_cluster(uuid4())

        assert face.is_clustered is True

    def test_is_clustered_when_not_assigned(self):
        """When face is not assigned to cluster, is_clustered should be False."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)

        assert face.is_clustered is False

    def test_has_crop_when_path_set(self):
        """When crop path is set, has_crop should be True."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)
        face.set_crop_path("/storage/crops/face.jpg")

        assert face.has_crop is True

    def test_has_crop_when_path_not_set(self):
        """When crop path is not set, has_crop should be False."""
        photo_id = uuid4()
        bbox = BoundingBox(x=100, y=150, width=200, height=200)
        face = Face.create(photo_id=photo_id, bbox=bbox)

        assert face.has_crop is False


class TestBoundingBox:
    """Tests for BoundingBox value object used by Face."""

    def test_create_bounding_box(self):
        """When creating bounding box, coordinates should be stored."""
        bbox = BoundingBox(x=100, y=150, width=200, height=250)

        assert bbox.x == 100
        assert bbox.y == 150
        assert bbox.width == 200
        assert bbox.height == 250

    def test_bounding_box_computed_properties(self):
        """When accessing computed properties, they should be correct."""
        bbox = BoundingBox(x=100, y=150, width=200, height=250)

        assert bbox.x2 == 300  # x + width
        assert bbox.y2 == 400  # y + height
        assert bbox.center == (200, 275)  # (x + width//2, y + height//2)
        assert bbox.area == 50000  # width * height

    def test_bounding_box_to_tuple(self):
        """When converting to tuple, format should be (x, y, w, h)."""
        bbox = BoundingBox(x=100, y=150, width=200, height=250)

        assert bbox.to_tuple() == (100, 150, 200, 250)

    def test_bounding_box_to_xyxy(self):
        """When converting to xyxy, format should be (x1, y1, x2, y2)."""
        bbox = BoundingBox(x=100, y=150, width=200, height=250)

        assert bbox.to_xyxy() == (100, 150, 300, 400)

    def test_bounding_box_from_xyxy(self):
        """When creating from xyxy, it should convert correctly."""
        bbox = BoundingBox.from_xyxy(x1=100, y1=150, x2=300, y2=400)

        assert bbox.x == 100
        assert bbox.y == 150
        assert bbox.width == 200
        assert bbox.height == 250

    def test_bounding_box_expand(self):
        """When expanding bounding box, it should grow in all directions."""
        bbox = BoundingBox(x=100, y=150, width=200, height=250)

        expanded = bbox.expand(margin=10)

        assert expanded.x == 90  # x - margin
        assert expanded.y == 140  # y - margin
        assert expanded.width == 220  # width + 2*margin
        assert expanded.height == 270  # height + 2*margin

    def test_bounding_box_expand_respects_zero_boundary(self):
        """When expanding near boundary, x and y should not go negative."""
        bbox = BoundingBox(x=5, y=5, width=100, height=100)

        expanded = bbox.expand(margin=10)

        assert expanded.x == 0  # max(0, 5 - 10)
        assert expanded.y == 0  # max(0, 5 - 10)

    def test_bounding_box_is_immutable(self):
        """When trying to modify bbox, it should raise error."""
        bbox = BoundingBox(x=100, y=150, width=200, height=250)

        with pytest.raises(Exception):  # dataclass frozen=True raises FrozenInstanceError
            bbox.x = 200

    def test_bounding_box_validation_negative_width(self):
        """When creating with negative width, it should raise error."""
        with pytest.raises(ValueError) as exc:
            BoundingBox(x=100, y=150, width=-10, height=250)

        assert "Width must be positive" in str(exc.value)

    def test_bounding_box_validation_negative_height(self):
        """When creating with negative height, it should raise error."""
        with pytest.raises(ValueError) as exc:
            BoundingBox(x=100, y=150, width=200, height=-10)

        assert "Height must be positive" in str(exc.value)

    def test_bounding_box_validation_negative_x(self):
        """When creating with negative x, it should raise error."""
        with pytest.raises(ValueError) as exc:
            BoundingBox(x=-10, y=150, width=200, height=250)

        assert "X coordinate cannot be negative" in str(exc.value)

    def test_bounding_box_validation_negative_y(self):
        """When creating with negative y, it should raise error."""
        with pytest.raises(ValueError) as exc:
            BoundingBox(x=100, y=-10, width=200, height=250)

        assert "Y coordinate cannot be negative" in str(exc.value)

    def test_bounding_box_validation_zero_dimensions(self):
        """When creating with zero dimensions, it should raise error."""
        with pytest.raises(ValueError):
            BoundingBox(x=100, y=150, width=0, height=250)

        with pytest.raises(ValueError):
            BoundingBox(x=100, y=150, width=200, height=0)
