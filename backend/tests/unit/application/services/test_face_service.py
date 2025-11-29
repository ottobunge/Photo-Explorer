"""Unit tests for FaceService with focus on merge_clusters and compensating transactions."""

import logging
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from app.application.ports.outbound import (
    FaceRepository,
    FileStorage,
    VectorStore,
)
from app.application.services.face_service import FaceService
from app.domain.entities import Face, FaceCluster
from app.domain.exceptions import EntityNotFoundException
from app.domain.value_objects import BoundingBox


class TestMergeClustersAtomic:
    """Tests for atomic merge_clusters operation with compensating transactions."""

    @pytest.fixture
    def mock_face_repo(self) -> Mock:
        """Mock face repository."""
        repo = Mock(spec=FaceRepository)
        repo.find_cluster_by_id = AsyncMock()
        repo.find_faces_by_ids = AsyncMock()
        repo.save_faces_batch = AsyncMock()
        repo.delete_cluster = AsyncMock()
        repo.save_cluster = AsyncMock()
        return repo

    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Mock vector store."""
        store = Mock(spec=VectorStore)
        store.update_face_payloads_batch = AsyncMock()
        return store

    @pytest.fixture
    def mock_file_storage(self) -> Mock:
        """Mock file storage."""
        return Mock(spec=FileStorage)

    @pytest.fixture
    def service(
        self,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        mock_file_storage: Mock,
    ) -> FaceService:
        """Create FaceService with mocked dependencies."""
        return FaceService(
            mock_face_repo,
            mock_file_storage,
            mock_vector_store,
        )

    @pytest.fixture
    def target_cluster(self) -> FaceCluster:
        """Create a target cluster for merging."""
        target_id = uuid4()
        cluster = FaceCluster.create(initial_face_id=uuid4())
        # Override ID for testing
        cluster._id = target_id  # type: ignore[attr-defined]
        return cluster

    @pytest.fixture
    def source_clusters(self) -> list[FaceCluster]:
        """Create source clusters for merging."""
        clusters = []
        for _ in range(2):
            cluster = FaceCluster.create(initial_face_id=uuid4())
            clusters.append(cluster)
        return clusters

    @pytest.fixture
    def sample_faces(self) -> list[Face]:
        """Create sample faces for testing."""
        faces = []
        for i in range(3):
            face = Face.create(
                photo_id=uuid4(),
                bbox=BoundingBox(x=i * 10, y=i * 20, width=100, height=120),
            )
            faces.append(face)
        return faces

    @pytest.mark.asyncio
    async def test_merge_clusters_success(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        target_cluster: FaceCluster,
        source_clusters: list[FaceCluster],
        sample_faces: list[Face],
    ) -> None:
        """When merge succeeds, target cluster should contain all faces."""
        # Arrange
        target_id = target_cluster.id.value
        source_ids = [c.id.value for c in source_clusters]

        # Set up source cluster face IDs
        source_clusters[0]._face_ids = [sample_faces[0].id.value, sample_faces[1].id.value]  # type: ignore[attr-defined]
        source_clusters[1]._face_ids = [sample_faces[2].id.value]  # type: ignore[attr-defined]

        # Setup mock returns
        mock_face_repo.find_cluster_by_id.side_effect = [
            target_cluster,  # Find target
            source_clusters[0],  # Find source 1
            source_clusters[1],  # Find source 2
        ]

        # Return sample faces when fetching from sources
        mock_face_repo.find_faces_by_ids.side_effect = [
            [sample_faces[0], sample_faces[1]],  # From source 1
            [sample_faces[2]],  # From source 2
        ]

        mock_face_repo.save_cluster.return_value = target_cluster

        # Act
        result = await service.merge_clusters(source_ids, target_id)

        # Assert
        assert result.id.value == target_id
        # Verify faces were saved with new cluster assignment
        assert mock_face_repo.save_faces_batch.called
        saved_faces = mock_face_repo.save_faces_batch.call_args[0][0]
        assert len(saved_faces) == 3
        for face in saved_faces:
            assert face.cluster_id == target_id

        # Verify vector store was updated in batch
        mock_vector_store.update_face_payloads_batch.assert_called_once()
        vector_updates = mock_vector_store.update_face_payloads_batch.call_args[0][0]
        assert len(vector_updates) == 3
        for face_id, payload in vector_updates:
            assert payload["cluster_id"] == str(target_id)

        # Verify source clusters were deleted
        assert mock_face_repo.delete_cluster.call_count == 2

    @pytest.mark.asyncio
    async def test_merge_clusters_target_not_found(
        self,
        service: FaceService,
        mock_face_repo: Mock,
    ) -> None:
        """When target cluster not found, should raise EntityNotFoundException."""
        # Arrange
        target_id = uuid4()
        source_ids = [uuid4()]
        mock_face_repo.find_cluster_by_id.return_value = None

        # Act & Assert
        with pytest.raises(EntityNotFoundException) as exc:
            await service.merge_clusters(source_ids, target_id)
        assert "Cluster" in str(exc.value)

    @pytest.mark.asyncio
    async def test_merge_clusters_ignores_missing_source(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        target_cluster: FaceCluster,
    ) -> None:
        """When source cluster not found, should skip and continue."""
        # Arrange
        target_id = target_cluster.id.value
        source_ids = [uuid4(), uuid4()]

        # First call returns target, subsequent calls return None (source not found)
        mock_face_repo.find_cluster_by_id.side_effect = [
            target_cluster,  # Find target
            None,  # Find source 1 (not found)
            None,  # Find source 2 (not found)
        ]

        mock_face_repo.save_cluster.return_value = target_cluster

        # Act
        result = await service.merge_clusters(source_ids, target_id)

        # Assert
        assert result.id.value == target_id
        # No faces should be updated (no batch updates)
        mock_vector_store.update_face_payloads_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_merge_clusters_ignores_self_merge(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        target_cluster: FaceCluster,
    ) -> None:
        """When source ID equals target ID, should skip it."""
        # Arrange
        target_id = target_cluster.id.value
        source_ids = [target_id]  # Merging cluster into itself

        mock_face_repo.find_cluster_by_id.return_value = target_cluster
        mock_face_repo.save_cluster.return_value = target_cluster

        # Act
        result = await service.merge_clusters(source_ids, target_id)

        # Assert
        assert result.id.value == target_id
        # No vector store updates should occur
        mock_vector_store.update_face_payloads_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_merge_clusters_vector_store_failure_triggers_compensation(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        target_cluster: FaceCluster,
        source_clusters: list[FaceCluster],
        sample_faces: list[Face],
    ) -> None:
        """When vector store fails, should compensate by reverting DB changes."""
        # Arrange
        target_id = target_cluster.id.value
        source_ids = [c.id.value for c in source_clusters]

        # Store original cluster IDs from the source clusters
        original_cluster_0 = source_clusters[0].id.value
        original_cluster_1 = source_clusters[1].id.value

        # Set up source cluster face IDs
        source_clusters[0]._face_ids = [sample_faces[0].id.value, sample_faces[1].id.value]  # type: ignore[attr-defined]
        source_clusters[1]._face_ids = [sample_faces[2].id.value]  # type: ignore[attr-defined]

        # Assign faces to their source clusters using the proper method
        sample_faces[0].assign_to_cluster(original_cluster_0)
        sample_faces[1].assign_to_cluster(original_cluster_0)
        sample_faces[2].assign_to_cluster(original_cluster_1)

        # Setup mock returns
        mock_face_repo.find_cluster_by_id.side_effect = [
            target_cluster,  # Find target
            source_clusters[0],  # Find source 1
            source_clusters[1],  # Find source 2
        ]

        mock_face_repo.find_faces_by_ids.side_effect = [
            [sample_faces[0], sample_faces[1]],  # From source 1
            [sample_faces[2]],  # From source 2
        ]

        # Make vector store fail on batch update
        mock_vector_store.update_face_payloads_batch.side_effect = [
            Exception("Vector store unavailable"),
            None,  # Compensation succeeds
        ]

        mock_face_repo.save_cluster.return_value = target_cluster

        # Act & Assert
        with pytest.raises(Exception, match="Vector store unavailable"):
            await service.merge_clusters(source_ids, target_id)

        # Verify compensation was attempted
        # save_faces_batch should be called twice:
        # 1. First for the merge updates
        # 2. Second for reverting in compensation
        assert mock_face_repo.save_faces_batch.call_count >= 2

        # Verify reverting vector store call was made
        assert mock_vector_store.update_face_payloads_batch.call_count >= 2

        # Check that the second call (compensation) reverts to original cluster IDs
        revert_call = mock_vector_store.update_face_payloads_batch.call_args_list[1]
        revert_updates = revert_call[0][0]

        # All reverted updates should point back to original clusters
        assert len(revert_updates) == 3
        for i, (face_id, payload) in enumerate(revert_updates):
            cluster_id = payload["cluster_id"]
            # Verify it's a string
            assert isinstance(cluster_id, str)
            # Verify it matches one of the original cluster IDs
            assert cluster_id in (str(original_cluster_0), str(original_cluster_1))

    @pytest.mark.asyncio
    async def test_merge_clusters_compensation_failure_logged_critically(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        target_cluster: FaceCluster,
        source_clusters: list[FaceCluster],
        sample_faces: list[Face],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When compensation itself fails, should log critical error."""
        # Arrange
        target_id = target_cluster.id.value
        source_ids = [c.id.value for c in source_clusters]

        # Store original cluster IDs
        original_cluster_0 = source_clusters[0].id.value
        original_cluster_1 = source_clusters[1].id.value

        # Set up source cluster face IDs
        source_clusters[0]._face_ids = [sample_faces[0].id.value]  # type: ignore[attr-defined]
        source_clusters[1]._face_ids = [sample_faces[1].id.value]  # type: ignore[attr-defined]

        # Assign faces to their source clusters using the proper method
        sample_faces[0].assign_to_cluster(original_cluster_0)
        sample_faces[1].assign_to_cluster(original_cluster_1)

        # Setup mock returns
        mock_face_repo.find_cluster_by_id.side_effect = [
            target_cluster,  # Find target
            source_clusters[0],  # Find source 1
            source_clusters[1],  # Find source 2
        ]

        mock_face_repo.find_faces_by_ids.side_effect = [
            [sample_faces[0]],  # From source 1
            [sample_faces[1]],  # From source 2
        ]

        # First vector store call fails, second (revert) also fails
        mock_vector_store.update_face_payloads_batch.side_effect = [
            Exception("Vector store down"),
            Exception("Still down"),
        ]

        # Act & Assert
        with caplog.at_level(logging.CRITICAL):
            with pytest.raises(Exception, match="Vector store down"):
                await service.merge_clusters(source_ids, target_id)

        # Verify critical error was logged during compensation
        assert "CRITICAL: Failed to compensate merge failure" in caplog.text
        assert "manual intervention may be required" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_merge_clusters_preserves_face_state_on_success(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        target_cluster: FaceCluster,
        source_clusters: list[FaceCluster],
        sample_faces: list[Face],
    ) -> None:
        """When merge succeeds, faces should have correct cluster assignment."""
        # Arrange
        target_id = target_cluster.id.value
        source_ids = [c.id.value for c in source_clusters]

        # Store original cluster IDs
        original_cluster_ids = {
            sample_faces[0].id.value: uuid4(),
            sample_faces[1].id.value: uuid4(),
            sample_faces[2].id.value: uuid4(),
        }

        # Set cluster IDs on faces before merge
        for face in sample_faces:
            face._cluster_id = original_cluster_ids[face.id.value]  # type: ignore[attr-defined]

        # Set up source cluster face IDs
        source_clusters[0]._face_ids = [sample_faces[0].id.value, sample_faces[1].id.value]  # type: ignore[attr-defined]
        source_clusters[1]._face_ids = [sample_faces[2].id.value]  # type: ignore[attr-defined]

        # Setup mock returns
        mock_face_repo.find_cluster_by_id.side_effect = [
            target_cluster,  # Find target
            source_clusters[0],  # Find source 1
            source_clusters[1],  # Find source 2
        ]

        mock_face_repo.find_faces_by_ids.side_effect = [
            [sample_faces[0], sample_faces[1]],  # From source 1
            [sample_faces[2]],  # From source 2
        ]

        mock_face_repo.save_cluster.return_value = target_cluster

        # Act
        await service.merge_clusters(source_ids, target_id)

        # Assert - get the faces from the save call
        saved_faces = mock_face_repo.save_faces_batch.call_args_list[0][0][0]

        # All saved faces should have target cluster ID
        for face in saved_faces:
            assert face.cluster_id == target_id, \
                f"Face {face.id.value} should have cluster {target_id}, but has {face.cluster_id}"


class TestMergeClustersEdgeCases:
    """Tests for edge cases in merge_clusters."""

    @pytest.fixture
    def mock_face_repo(self) -> Mock:
        """Mock face repository."""
        repo = Mock(spec=FaceRepository)
        repo.find_cluster_by_id = AsyncMock()
        repo.find_faces_by_ids = AsyncMock()
        repo.save_faces_batch = AsyncMock()
        repo.delete_cluster = AsyncMock()
        repo.save_cluster = AsyncMock()
        return repo

    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Mock vector store."""
        store = Mock(spec=VectorStore)
        store.update_face_payloads_batch = AsyncMock()
        return store

    @pytest.fixture
    def mock_file_storage(self) -> Mock:
        """Mock file storage."""
        return Mock(spec=FileStorage)

    @pytest.fixture
    def service(
        self,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        mock_file_storage: Mock,
    ) -> FaceService:
        """Create FaceService with mocked dependencies."""
        return FaceService(
            mock_face_repo,
            mock_file_storage,
            mock_vector_store,
        )

    @pytest.mark.asyncio
    async def test_merge_empty_source_list(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
    ) -> None:
        """When merging empty source list, should not modify anything."""
        # Arrange
        target_cluster = FaceCluster.create(initial_face_id=uuid4())
        target_id = target_cluster.id.value

        mock_face_repo.find_cluster_by_id.return_value = target_cluster
        mock_face_repo.save_cluster.return_value = target_cluster

        # Act
        result = await service.merge_clusters([], target_id)

        # Assert
        assert result.id.value == target_id
        # No vector store updates should happen
        mock_vector_store.update_face_payloads_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_merge_clusters_with_many_faces(
        self,
        service: FaceService,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
    ) -> None:
        """When merging many faces, should handle large batch efficiently."""
        # Arrange
        target_cluster = FaceCluster.create(initial_face_id=uuid4())
        target_id = target_cluster.id.value
        source_id = uuid4()

        # Create 100 faces
        many_faces = [
            Face.create(
                photo_id=uuid4(),
                bbox=BoundingBox(x=i * 10, y=i * 20, width=100, height=120),
            )
            for i in range(100)
        ]

        source_cluster = FaceCluster.create(initial_face_id=many_faces[0].id.value)
        source_cluster._face_ids = [f.id.value for f in many_faces]  # type: ignore[attr-defined]

        mock_face_repo.find_cluster_by_id.side_effect = [
            target_cluster,
            source_cluster,
        ]
        mock_face_repo.find_faces_by_ids.return_value = many_faces
        mock_face_repo.save_cluster.return_value = target_cluster

        # Act
        await service.merge_clusters([source_id], target_id)

        # Assert
        # All faces should be saved in single batch call
        assert mock_face_repo.save_faces_batch.call_count == 1
        saved_faces = mock_face_repo.save_faces_batch.call_args[0][0]
        assert len(saved_faces) == 100

        # Vector store should get batch update with all 100 faces
        mock_vector_store.update_face_payloads_batch.assert_called_once()
        vector_updates = mock_vector_store.update_face_payloads_batch.call_args[0][0]
        assert len(vector_updates) == 100


class TestFaceServiceOtherOperations:
    """Tests for other FaceService operations to ensure merge doesn't break them."""

    @pytest.fixture
    def mock_face_repo(self) -> Mock:
        """Mock face repository."""
        repo = Mock(spec=FaceRepository)
        repo.find_all_clusters = AsyncMock()
        repo.find_cluster_by_id = AsyncMock()
        repo.save_cluster = AsyncMock()
        return repo

    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Mock vector store."""
        return Mock(spec=VectorStore)

    @pytest.fixture
    def mock_file_storage(self) -> Mock:
        """Mock file storage."""
        return Mock(spec=FileStorage)

    @pytest.fixture
    def service(
        self,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        mock_file_storage: Mock,
    ) -> FaceService:
        """Create FaceService with mocked dependencies."""
        return FaceService(
            mock_face_repo,
            mock_file_storage,
            mock_vector_store,
        )

    @pytest.mark.asyncio
    async def test_list_clusters(
        self,
        service: FaceService,
        mock_face_repo: Mock,
    ) -> None:
        """Test list_clusters operation."""
        # Arrange
        clusters = [
            FaceCluster.create(initial_face_id=uuid4()),
            FaceCluster.create(initial_face_id=uuid4()),
        ]
        mock_face_repo.find_all_clusters.return_value = clusters

        # Act
        result = await service.list_clusters()

        # Assert
        assert len(result) == 2
        assert all(isinstance(c, FaceCluster) for c in result)

    @pytest.mark.asyncio
    async def test_get_cluster(
        self,
        service: FaceService,
        mock_face_repo: Mock,
    ) -> None:
        """Test get_cluster operation."""
        # Arrange
        cluster = FaceCluster.create(initial_face_id=uuid4())
        cluster_id = cluster.id.value
        mock_face_repo.find_cluster_by_id.return_value = cluster

        # Act
        result = await service.get_cluster(cluster_id)

        # Assert
        assert result is not None
        assert result.id.value == cluster_id

    @pytest.mark.asyncio
    async def test_name_cluster(
        self,
        service: FaceService,
        mock_face_repo: Mock,
    ) -> None:
        """Test name_cluster operation."""
        # Arrange
        cluster = FaceCluster.create(initial_face_id=uuid4())
        cluster_id = cluster.id.value
        name = "John Doe"

        mock_face_repo.find_cluster_by_id.return_value = cluster
        mock_face_repo.save_cluster.return_value = cluster

        # Act
        result = await service.name_cluster(cluster_id, name)

        # Assert
        assert result.name == name
        mock_face_repo.save_cluster.assert_called_once()
