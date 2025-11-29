"""Unit tests for FaceRepositoryPostgres batch methods."""

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.postgres.repositories.face_repository import (
    FaceRepositoryPostgres,
)
from app.domain.entities import Face, FaceCluster
from app.domain.value_objects import BoundingBox, FaceClusterId, FaceId

pytestmark = pytest.mark.asyncio


class TestFaceRepositoryBatchMethods:
    """Unit tests for batch repository methods."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.get = AsyncMock()
        session.add = Mock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def face_repo(self, mock_session: Mock) -> FaceRepositoryPostgres:
        """Create FaceRepositoryPostgres with mock session."""
        return FaceRepositoryPostgres(mock_session)

    @pytest.fixture
    def sample_face(self) -> Face:
        """Create a sample face entity."""
        return Face.create(
            photo_id=uuid4(),
            bbox=BoundingBox(x=10, y=20, width=100, height=120),
            quality_score=0.95,
            detection_confidence=0.98,
        )

    @pytest.fixture
    def sample_faces(self) -> list[Face]:
        """Create multiple sample face entities."""
        photo_id = uuid4()
        return [
            Face.create(
                photo_id=photo_id,
                bbox=BoundingBox(x=i * 10, y=i * 20, width=100, height=120),
                quality_score=0.9 + i * 0.01,
                detection_confidence=0.95,
            )
            for i in range(5)
        ]


class TestFindFacesByIds(TestFaceRepositoryBatchMethods):
    """Tests for find_faces_by_ids method."""

    @pytest.mark.asyncio
    async def test_find_faces_by_ids_empty_list(
        self,
        face_repo: FaceRepositoryPostgres,
    ) -> None:
        """When called with empty list, should return empty list."""
        # Act
        result = await face_repo.find_faces_by_ids([])

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_find_faces_by_ids_single_id(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
        sample_face: Face,
    ) -> None:
        """When finding single face, should return it."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import FaceModel

        # Mock database result
        face_model = Mock(spec=FaceModel)
        face_model.id = sample_face.id.value
        face_model.photo_id = sample_face.photo_id
        face_model.cluster_id = None
        face_model.bbox_x = 10
        face_model.bbox_y = 20
        face_model.bbox_width = 100
        face_model.bbox_height = 120
        face_model.crop_path = None
        face_model.quality_score = 0.95
        face_model.detection_confidence = 0.98
        face_model.created_at = datetime.now(timezone.utc)

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[face_model])))
        mock_session.execute.return_value = mock_result

        # Act
        result = await face_repo.find_faces_by_ids([sample_face.id.value])

        # Assert
        assert len(result) == 1
        assert result[0].id.value == sample_face.id.value

    @pytest.mark.asyncio
    async def test_find_faces_by_ids_multiple(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
        sample_faces: list[Face],
    ) -> None:
        """When finding multiple faces, should return all in one query."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import FaceModel

        face_models = []
        for face in sample_faces:
            model = Mock(spec=FaceModel)
            model.id = face.id.value
            model.photo_id = face.photo_id
            model.cluster_id = None
            model.bbox_x = face.bbox.x
            model.bbox_y = face.bbox.y
            model.bbox_width = face.bbox.width
            model.bbox_height = face.bbox.height
            model.crop_path = None
            model.quality_score = face.quality_score
            model.detection_confidence = face.detection_confidence
            model.created_at = datetime.now(timezone.utc)
            face_models.append(model)

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=face_models)))
        mock_session.execute.return_value = mock_result

        # Act
        ids = [f.id.value for f in sample_faces]
        result = await face_repo.find_faces_by_ids(ids)

        # Assert
        assert len(result) == len(sample_faces)
        assert mock_session.execute.call_count == 1  # Single query


class TestSaveFacesBatch(TestFaceRepositoryBatchMethods):
    """Tests for save_faces_batch method."""

    @pytest.mark.asyncio
    async def test_save_faces_batch_empty_list(
        self,
        face_repo: FaceRepositoryPostgres,
    ) -> None:
        """When called with empty list, should return empty list."""
        # Act
        result = await face_repo.save_faces_batch([])

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_save_faces_batch_creates_new(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
        sample_faces: list[Face],
    ) -> None:
        """When saving new faces, should create them all."""
        # Arrange - mock that none exist yet
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        mock_session.execute.return_value = mock_result

        # Act
        result = await face_repo.save_faces_batch(sample_faces)

        # Assert
        assert len(result) == len(sample_faces)
        assert mock_session.add.call_count == len(sample_faces)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_faces_batch_updates_existing(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
        sample_faces: list[Face],
    ) -> None:
        """When saving existing faces, should update them."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import FaceModel

        # Assign cluster IDs to faces
        cluster_id = uuid4()
        for face in sample_faces:
            face.assign_to_cluster(cluster_id)

        # Mock existing face models
        existing_models = []
        for face in sample_faces:
            model = Mock(spec=FaceModel)
            model.id = face.id.value
            model.photo_id = face.photo_id
            model.cluster_id = None  # Not yet assigned
            model.bbox_x = face.bbox.x
            model.bbox_y = face.bbox.y
            model.bbox_width = face.bbox.width
            model.bbox_height = face.bbox.height
            model.crop_path = None
            model.quality_score = face.quality_score
            model.detection_confidence = face.detection_confidence
            model.created_at = datetime.now(timezone.utc)
            existing_models.append(model)

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=existing_models)))
        mock_session.execute.return_value = mock_result

        # Act
        result = await face_repo.save_faces_batch(sample_faces)

        # Assert
        assert len(result) == len(sample_faces)
        # Verify cluster_id was updated on models
        for model in existing_models:
            assert model.cluster_id == cluster_id
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_faces_batch_mixed_new_and_existing(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
        sample_faces: list[Face],
    ) -> None:
        """When batch contains both new and existing faces, should handle both."""
        # Arrange
        from app.adapters.outbound.persistence.postgres.models import FaceModel

        # Mock that first 2 exist, last 3 are new
        existing_models = []
        for i in range(2):
            face = sample_faces[i]
            model = Mock(spec=FaceModel)
            model.id = face.id.value
            model.photo_id = face.photo_id
            model.cluster_id = None
            model.bbox_x = face.bbox.x
            model.bbox_y = face.bbox.y
            model.bbox_width = face.bbox.width
            model.bbox_height = face.bbox.height
            model.crop_path = None
            model.quality_score = face.quality_score
            model.detection_confidence = face.detection_confidence
            model.created_at = datetime.now(timezone.utc)
            existing_models.append(model)

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=existing_models)))
        mock_session.execute.return_value = mock_result

        # Act
        result = await face_repo.save_faces_batch(sample_faces)

        # Assert
        assert len(result) == len(sample_faces)
        assert mock_session.add.call_count == 3  # 3 new faces added
        mock_session.flush.assert_called_once()


class TestCountPhotosByCluster(TestFaceRepositoryBatchMethods):
    """Tests for count_photos_by_cluster method."""

    @pytest.mark.asyncio
    async def test_count_photos_by_cluster_accurate(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When counting photos, should return accurate count without loading photos."""
        # Arrange
        cluster_id = uuid4()
        expected_count = 15

        mock_result = Mock()
        mock_result.scalar_one = Mock(return_value=expected_count)
        mock_session.execute.return_value = mock_result

        # Act
        count = await face_repo.count_photos_by_cluster(cluster_id)

        # Assert
        assert count == expected_count
        assert isinstance(count, int)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_photos_by_cluster_zero(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When cluster has no photos, should return 0."""
        # Arrange
        cluster_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one = Mock(return_value=0)
        mock_session.execute.return_value = mock_result

        # Act
        count = await face_repo.count_photos_by_cluster(cluster_id)

        # Assert
        assert count == 0


class TestBatchUpdateCluster(TestFaceRepositoryBatchMethods):
    """Tests for batch_update_cluster method."""

    @pytest.mark.asyncio
    async def test_batch_update_cluster_assigns_faces(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When updating cluster for multiple faces, should update all at once."""
        # Arrange
        face_ids = [uuid4() for _ in range(10)]
        cluster_id = uuid4()

        mock_result = Mock()
        mock_result.rowcount = len(face_ids)
        mock_session.execute.return_value = mock_result

        # Act
        updated_count = await face_repo.batch_update_cluster(face_ids, cluster_id)

        # Assert
        assert updated_count == len(face_ids)
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_update_cluster_unassigns_faces(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When cluster_id is None, should unassign faces from cluster."""
        # Arrange
        face_ids = [uuid4() for _ in range(5)]

        mock_result = Mock()
        mock_result.rowcount = len(face_ids)
        mock_session.execute.return_value = mock_result

        # Act
        updated_count = await face_repo.batch_update_cluster(face_ids, None)

        # Assert
        assert updated_count == len(face_ids)

    @pytest.mark.asyncio
    async def test_batch_update_cluster_empty_list(
        self,
        face_repo: FaceRepositoryPostgres,
    ) -> None:
        """When called with empty list, should return 0."""
        # Act
        updated_count = await face_repo.batch_update_cluster([], uuid4())

        # Assert
        assert updated_count == 0


class TestGetCoAppearances(TestFaceRepositoryBatchMethods):
    """Tests for get_co_appearances method."""

    @pytest.mark.asyncio
    async def test_get_co_appearances_all_clusters(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When getting all co-appearances, should return cluster pairs."""
        # Arrange
        cluster_a = uuid4()
        cluster_b = uuid4()
        cluster_c = uuid4()

        mock_rows = [
            Mock(cluster_a=cluster_a, cluster_b=cluster_b, photo_count=5),
            Mock(cluster_a=cluster_a, cluster_b=cluster_c, photo_count=3),
            Mock(cluster_a=cluster_b, cluster_b=cluster_c, photo_count=2),
        ]
        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_rows)
        mock_session.execute.return_value = mock_result

        # Act
        co_appearances = await face_repo.get_co_appearances()

        # Assert
        assert len(co_appearances) == 3
        assert co_appearances[0] == (cluster_a, cluster_b, 5)
        assert co_appearances[1] == (cluster_a, cluster_c, 3)
        assert co_appearances[2] == (cluster_b, cluster_c, 2)

    @pytest.mark.asyncio
    async def test_get_co_appearances_for_specific_cluster(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When filtering by cluster_id, should return only that cluster's pairs."""
        # Arrange
        target_cluster = uuid4()
        other_cluster_a = uuid4()
        other_cluster_b = uuid4()

        mock_rows = [
            Mock(cluster_a=target_cluster, cluster_b=other_cluster_a, photo_count=5),
            Mock(cluster_a=target_cluster, cluster_b=other_cluster_b, photo_count=3),
        ]
        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_rows)
        mock_session.execute.return_value = mock_result

        # Act
        co_appearances = await face_repo.get_co_appearances(cluster_id=target_cluster)

        # Assert
        assert len(co_appearances) == 2
        # All results should involve target_cluster
        for cluster_a, cluster_b, count in co_appearances:
            assert target_cluster in (cluster_a, cluster_b)


class TestGetSharedPhotos(TestFaceRepositoryBatchMethods):
    """Tests for get_shared_photos method."""

    @pytest.mark.asyncio
    async def test_get_shared_photos_returns_photo_ids(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When getting shared photos, should return unique photo IDs."""
        # Arrange
        person_a = uuid4()
        person_b = uuid4()
        photo_ids = [uuid4() for _ in range(10)]

        mock_rows = [(photo_id,) for photo_id in photo_ids]
        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_rows)
        mock_session.execute.return_value = mock_result

        # Act
        shared_photos = await face_repo.get_shared_photos(person_a, person_b)

        # Assert
        assert len(shared_photos) == len(photo_ids)
        assert all(isinstance(pid, UUID) for pid in shared_photos)

    @pytest.mark.asyncio
    async def test_get_shared_photos_no_overlap(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When people have no shared photos, should return empty list."""
        # Arrange
        person_a = uuid4()
        person_b = uuid4()

        mock_result = Mock()
        mock_result.all = Mock(return_value=[])
        mock_session.execute.return_value = mock_result

        # Act
        shared_photos = await face_repo.get_shared_photos(person_a, person_b)

        # Assert
        assert shared_photos == []


class TestCountPhotosByClustersBatch:
    """Unit tests for batch photo counting method."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock async session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def face_repo(self, mock_session: Mock) -> FaceRepositoryPostgres:
        """Create FaceRepositoryPostgres with mock session."""
        return FaceRepositoryPostgres(mock_session)

    @pytest.mark.asyncio
    async def test_count_photos_by_clusters_batch_empty_list(
        self,
        face_repo: FaceRepositoryPostgres,
    ) -> None:
        """When given empty cluster list, should return empty dict."""
        # Act
        result = await face_repo.count_photos_by_clusters_batch([])

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    async def test_count_photos_by_clusters_batch_single_cluster(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When given single cluster, should return correct photo count."""
        # Arrange
        cluster_id = uuid4()
        mock_row = Mock()
        mock_row.cluster_id = cluster_id
        mock_row.photo_count = 15

        mock_result = Mock()
        mock_result.all = Mock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Act
        result = await face_repo.count_photos_by_clusters_batch([cluster_id])

        # Assert
        assert result == {cluster_id: 15}

    @pytest.mark.asyncio
    async def test_count_photos_by_clusters_batch_multiple_clusters(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When given multiple clusters, should return counts for all."""
        # Arrange
        cluster_ids = [uuid4(), uuid4(), uuid4()]
        mock_rows = [
            Mock(cluster_id=cluster_ids[0], photo_count=10),
            Mock(cluster_id=cluster_ids[1], photo_count=25),
            Mock(cluster_id=cluster_ids[2], photo_count=5),
        ]

        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_rows)
        mock_session.execute.return_value = mock_result

        # Act
        result = await face_repo.count_photos_by_clusters_batch(cluster_ids)

        # Assert
        assert len(result) == 3
        assert result[cluster_ids[0]] == 10
        assert result[cluster_ids[1]] == 25
        assert result[cluster_ids[2]] == 5

    @pytest.mark.asyncio
    async def test_count_photos_by_clusters_batch_cluster_with_zero_photos(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """When cluster has no photos, should default to 0."""
        # Arrange
        cluster_ids = [uuid4(), uuid4()]
        # Only one cluster has results
        mock_rows = [Mock(cluster_id=cluster_ids[0], photo_count=5)]

        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_rows)
        mock_session.execute.return_value = mock_result

        # Act
        result = await face_repo.count_photos_by_clusters_batch(cluster_ids)

        # Assert
        assert len(result) == 2
        assert result[cluster_ids[0]] == 5
        assert result[cluster_ids[1]] == 0

    @pytest.mark.asyncio
    async def test_count_photos_by_clusters_batch_uses_single_query(
        self,
        face_repo: FaceRepositoryPostgres,
        mock_session: Mock,
    ) -> None:
        """Should execute exactly one query regardless of cluster count."""
        # Arrange
        cluster_ids = [uuid4() for _ in range(50)]
        mock_result = Mock()
        mock_result.all = Mock(return_value=[])
        mock_session.execute.return_value = mock_result

        # Act
        await face_repo.count_photos_by_clusters_batch(cluster_ids)

        # Assert - should only call execute once
        mock_session.execute.assert_called_once()
