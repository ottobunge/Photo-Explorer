"""Unit tests for FaceCluster entity."""

from uuid import uuid4

import pytest

from app.domain.entities import FaceCluster
from app.domain.exceptions import InvalidOperationException


class TestFaceClusterCreation:
    """Tests for FaceCluster entity creation."""

    def test_create_empty_cluster(self):
        """When creating cluster without face, it should be empty."""
        cluster = FaceCluster.create()

        assert cluster.face_count == 0
        assert cluster.is_empty is True
        assert cluster.name is None

    def test_create_cluster_with_initial_face(self):
        """When creating cluster with face, it should contain that face."""
        face_id = uuid4()
        cluster = FaceCluster.create(initial_face_id=face_id)

        assert cluster.face_count == 1
        assert face_id in cluster.face_ids
        assert cluster.representative_face_id == face_id


class TestFaceClusterNaming:
    """Tests for FaceCluster naming operations."""

    def test_set_name(self):
        """When naming cluster, name should be set and is_named should be True."""
        cluster = FaceCluster.create()

        cluster.set_name("John Doe")

        assert cluster.name == "John Doe"
        assert cluster.is_named is True

    def test_set_name_trims_whitespace(self):
        """When setting name with whitespace, it should be trimmed."""
        cluster = FaceCluster.create()

        cluster.set_name("  Jane Doe  ")

        assert cluster.name == "Jane Doe"

    def test_clear_name(self):
        """When clearing name, is_named should be False."""
        cluster = FaceCluster.create()
        cluster.set_name("John Doe")

        cluster.clear_name()

        assert cluster.name is None
        assert cluster.is_named is False


class TestFaceClusterFaceOperations:
    """Tests for FaceCluster face management."""

    def test_add_face(self):
        """When adding face, it should be in face_ids."""
        cluster = FaceCluster.create()
        face_id = uuid4()

        cluster.add_face(face_id)

        assert face_id in cluster.face_ids
        assert cluster.face_count == 1

    def test_add_face_sets_representative_if_first(self):
        """When adding first face, it should become representative."""
        cluster = FaceCluster.create()
        face_id = uuid4()

        cluster.add_face(face_id)

        assert cluster.representative_face_id == face_id

    def test_add_face_does_not_change_representative(self):
        """When adding second face, representative should not change."""
        cluster = FaceCluster.create()
        first_face = uuid4()
        second_face = uuid4()

        cluster.add_face(first_face)
        cluster.add_face(second_face)

        assert cluster.representative_face_id == first_face

    def test_remove_face(self):
        """When removing face, it should not be in face_ids."""
        face_id = uuid4()
        cluster = FaceCluster.create(initial_face_id=face_id)

        cluster.remove_face(face_id)

        assert face_id not in cluster.face_ids
        assert cluster.is_empty is True

    def test_remove_representative_updates_to_next(self):
        """When removing representative, next face should become representative."""
        cluster = FaceCluster.create()
        first_face = uuid4()
        second_face = uuid4()
        cluster.add_face(first_face)
        cluster.add_face(second_face)

        cluster.remove_face(first_face)

        assert cluster.representative_face_id == second_face

    def test_set_representative(self):
        """When setting representative, it should be updated."""
        cluster = FaceCluster.create()
        first_face = uuid4()
        second_face = uuid4()
        cluster.add_face(first_face)
        cluster.add_face(second_face)

        cluster.set_representative(second_face)

        assert cluster.representative_face_id == second_face

    def test_set_representative_non_member_raises_error(self):
        """When setting representative to non-member, it should raise error."""
        cluster = FaceCluster.create()
        cluster.add_face(uuid4())
        non_member = uuid4()

        with pytest.raises(InvalidOperationException):
            cluster.set_representative(non_member)


class TestFaceClusterMerge:
    """Tests for FaceCluster merge operations."""

    def test_merge_moves_faces(self):
        """When merging, all faces should move to target cluster."""
        cluster1 = FaceCluster.create()
        cluster2 = FaceCluster.create()
        face1 = uuid4()
        face2 = uuid4()
        cluster1.add_face(face1)
        cluster2.add_face(face2)

        moved = cluster1.merge_from(cluster2)

        assert face2 in cluster1.face_ids
        assert face2 in moved
        assert cluster1.face_count == 2

    def test_merge_preserves_existing_name(self):
        """When merging with named cluster, existing name should be kept."""
        cluster1 = FaceCluster.create()
        cluster2 = FaceCluster.create()
        cluster1.set_name("John")
        cluster2.set_name("Johnny")

        cluster1.merge_from(cluster2)

        assert cluster1.name == "John"

    def test_merge_takes_source_name_if_target_unnamed(self):
        """When target is unnamed, it should take source's name."""
        cluster1 = FaceCluster.create()
        cluster2 = FaceCluster.create()
        cluster2.set_name("John")

        cluster1.merge_from(cluster2)

        assert cluster1.name == "John"
