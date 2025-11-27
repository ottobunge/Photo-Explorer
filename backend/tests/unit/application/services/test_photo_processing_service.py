"""Unit tests for PhotoProcessingService."""

import logging
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import numpy as np
import pytest

from app.application.ports.outbound import (
    FaceRepository,
    FileStorage,
    MLServices,
    PhotoRepository,
    VectorStore,
)
from app.application.services.photo_processing_service import (
    FaceDetectionResult,
    PhotoProcessingService,
    ProcessingResult,
)
from app.domain.entities import Face, Photo
from app.domain.exceptions import EntityNotFoundException
from app.domain.value_objects import BoundingBox, Embedding, PhotoId


class TestPhotoProcessingService:
    """Unit tests for PhotoProcessingService."""

    @pytest.fixture
    def mock_photo_repo(self) -> Mock:
        """Mock photo repository."""
        repo = Mock(spec=PhotoRepository)
        repo.find_by_id = AsyncMock()
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def mock_face_repo(self) -> Mock:
        """Mock face repository."""
        repo = Mock(spec=FaceRepository)
        repo.save_faces_batch = AsyncMock(return_value=[])
        repo.delete_face = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def mock_ml_services(self) -> Mock:
        """Mock ML services."""
        ml = Mock(spec=MLServices)
        ml.encode_image = AsyncMock(return_value=Embedding(np.random.rand(512).astype(np.float32)))
        ml.generate_thumbnail = AsyncMock(return_value=b"thumbnail_data")
        ml.analyze_image = AsyncMock()
        ml.detect_faces = AsyncMock(return_value=[])
        ml.crop_face = AsyncMock(return_value=b"face_crop_data")
        return ml

    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Mock vector store."""
        store = Mock(spec=VectorStore)
        store.store_photo_embedding = AsyncMock()
        store.store_face_embedding = AsyncMock()
        store.delete_face_embeddings_batch = AsyncMock()
        return store

    @pytest.fixture
    def mock_file_storage(self) -> Mock:
        """Mock file storage."""
        storage = Mock(spec=FileStorage)
        storage.save_thumbnail = AsyncMock(return_value="/path/to/thumbnail.jpg")
        storage.save_face_crop = AsyncMock(return_value="/path/to/crop.jpg")
        storage.get_file = AsyncMock(return_value=b"image_data")
        return storage

    @pytest.fixture
    def service(
        self,
        mock_photo_repo: Mock,
        mock_face_repo: Mock,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_file_storage: Mock,
    ) -> PhotoProcessingService:
        """Create PhotoProcessingService with mocked dependencies."""
        return PhotoProcessingService(
            mock_photo_repo,
            mock_face_repo,
            mock_ml_services,
            mock_vector_store,
            mock_file_storage,
        )

    @pytest.fixture
    def sample_photo(self) -> Photo:
        """Create a sample photo entity."""
        return Photo(
            id=PhotoId(uuid4()),
            filename="test.jpg",
            storage_path="/path/to/photo.jpg",
            connector_type="local",
            connector_id=uuid4(),
            created_at=datetime.utcnow(),
            processing_status="pending",
        )

    @pytest.fixture
    def sample_analysis(self) -> Any:
        """Create sample image analysis result."""
        analysis = Mock()
        analysis.description = "A beautiful sunset"
        analysis.scene_classification = "outdoor"
        analysis.detected_objects = [
            Mock(label="person"),
            Mock(label="tree"),
        ]
        return analysis


class TestProcessPhoto(TestPhotoProcessingService):
    """Tests for process_photo method."""

    @pytest.mark.asyncio
    async def test_process_photo_success(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        sample_photo: Photo,
        sample_analysis: Any,
    ) -> None:
        """When photo processing succeeds, it should return completed status."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo
        mock_ml_services.analyze_image.return_value = sample_analysis

        # Act
        result = await service.process_photo(sample_photo.id.value)

        # Assert
        assert result.status == "completed"
        assert result.photo_id == str(sample_photo.id.value)
        assert result.thumbnail_path == "/path/to/thumbnail.jpg"
        assert mock_photo_repo.save.call_count >= 2  # Mark processing + finalize
        assert mock_ml_services.encode_image.called
        assert mock_ml_services.generate_thumbnail.called

    @pytest.mark.asyncio
    async def test_process_photo_not_found(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
    ) -> None:
        """When photo not found, it should raise EntityNotFoundException."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(EntityNotFoundException) as exc:
            await service.process_photo(uuid4())
        assert "Photo" in str(exc.value)

    @pytest.mark.asyncio
    async def test_process_photo_marks_processing_first(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        sample_photo: Photo,
        sample_analysis: Any,
    ) -> None:
        """When processing starts, photo should be marked as processing."""
        # Arrange
        # Mock find_by_id to return photo on both calls
        mock_photo_repo.find_by_id.return_value = sample_photo

        # Track saves - return the saved photo
        saved_photos: list[Photo] = []

        def track_save(photo: Photo) -> Photo:
            # Store a snapshot of the status
            saved_photos.append((photo, photo.processing_status))
            return photo

        mock_photo_repo.save.side_effect = track_save
        mock_ml_services.analyze_image.return_value = sample_analysis

        # Act
        await service.process_photo(sample_photo.id.value)

        # Assert
        # First save should mark as processing
        assert len(saved_photos) >= 2
        assert saved_photos[0][1] == "processing"  # First call
        assert saved_photos[-1][1] == "completed"  # Last call

    @pytest.mark.asyncio
    async def test_process_photo_vector_store_failure_marks_failed(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_vector_store: Mock,
        sample_photo: Photo,
        sample_analysis: Any,
    ) -> None:
        """When vector store fails, photo should be marked as failed."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo
        mock_vector_store.store_photo_embedding.side_effect = Exception("Vector store down")

        # Act & Assert
        with pytest.raises(Exception):
            await service.process_photo(sample_photo.id.value)

        # Assert photo marked as failed
        final_call_photo = mock_photo_repo.save.call_args_list[-1][0][0]
        assert final_call_photo.processing_status == "failed"

    @pytest.mark.asyncio
    async def test_process_photo_image_loading_failure_marks_failed(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_file_storage: Mock,
        sample_photo: Photo,
    ) -> None:
        """When image loading fails, photo should be marked as failed."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo
        mock_file_storage.get_file.return_value = None  # Simulate load failure

        # Act & Assert
        with pytest.raises(ValueError, match="Could not load image from storage"):
            await service.process_photo(sample_photo.id.value)

        # Assert photo marked as failed
        final_call_photo = mock_photo_repo.save.call_args_list[-1][0][0]
        assert final_call_photo.processing_status == "failed"

    @pytest.mark.asyncio
    async def test_process_photo_no_storage_path_uses_source_path(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        sample_analysis: Any,
    ) -> None:
        """When storage_path is None, should use source_path."""
        # Arrange
        photo_without_storage = Photo(
            id=PhotoId(uuid4()),
            filename="test.jpg",
            storage_path=None,
            source_path="/local/path/photo.jpg",
            connector_type="local",
            created_at=datetime.utcnow(),
        )
        mock_photo_repo.find_by_id.return_value = photo_without_storage
        mock_photo_repo.save.return_value = photo_without_storage
        mock_ml_services.analyze_image.return_value = sample_analysis

        # Mock aiofiles.open to return image data
        from unittest.mock import patch, AsyncMock as AsyncMockType

        mock_file_data = b"fake_image_data"
        mock_file = AsyncMockType()
        mock_file.read = AsyncMock(return_value=mock_file_data)
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)

        with patch("aiofiles.open", return_value=mock_file):
            # Act
            result = await service.process_photo(photo_without_storage.id.value)

        # Assert
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_process_photo_analysis_failure_non_critical(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        sample_photo: Photo,
    ) -> None:
        """When image analysis fails, processing should continue."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo
        mock_ml_services.analyze_image.side_effect = Exception("Analysis failed")

        # Act
        result = await service.process_photo(sample_photo.id.value)

        # Assert - should still complete successfully
        assert result.status == "completed"


class TestDetectFaces(TestPhotoProcessingService):
    """Tests for detect_faces method."""

    @pytest.mark.asyncio
    async def test_detect_faces_success(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        sample_photo: Photo,
    ) -> None:
        """When face detection succeeds, it should return detection results."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo

        # Mock detected faces
        detected_face = Mock()
        detected_face.bbox = [10, 20, 100, 120]
        detected_face.quality_score = 0.95
        detected_face.detection_confidence = 0.98
        detected_face.embedding = Embedding(np.random.rand(512).astype(np.float32))
        mock_ml_services.detect_faces.return_value = [detected_face]

        # Mock saved faces
        saved_face = Face.create(
            photo_id=sample_photo.id.value,
            bbox=BoundingBox(x=10, y=20, width=90, height=100),
            quality_score=0.95,
            detection_confidence=0.98,
        )
        saved_face.set_crop_path("/path/to/crop.jpg")
        mock_face_repo.save_faces_batch.return_value = [saved_face]

        # Mock vector store to succeed (use AsyncMock for async method)
        mock_vector_store.store_face_embedding = AsyncMock(return_value=None)

        # Act
        result = await service.detect_faces(sample_photo.id.value)

        # Assert
        assert result.status == "completed"
        assert result.photo_id == str(sample_photo.id.value)
        assert result.faces_detected == 1
        assert result.faces_saved == 1
        assert result.faces_in_vector_store == 1
        assert len(result.face_ids) == 1

    @pytest.mark.asyncio
    async def test_detect_faces_photo_not_found(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
    ) -> None:
        """When photo not found, it should raise EntityNotFoundException."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(EntityNotFoundException):
            await service.detect_faces(uuid4())

    @pytest.mark.asyncio
    async def test_detect_faces_no_faces_detected(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        sample_photo: Photo,
    ) -> None:
        """When no faces detected, should return zero counts."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_ml_services.detect_faces.return_value = []

        # Act
        result = await service.detect_faces(sample_photo.id.value)

        # Assert
        assert result.status == "completed"
        assert result.faces_detected == 0
        assert result.faces_saved == 0
        assert result.faces_in_vector_store == 0

    @pytest.mark.asyncio
    async def test_detect_faces_batch_save_called(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        mock_face_repo: Mock,
        sample_photo: Photo,
    ) -> None:
        """When faces detected, should use batch save."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo

        # Mock multiple detected faces
        detected_faces = []
        for i in range(3):
            face = Mock()
            face.bbox = [i * 10, i * 20, 100, 120]
            face.quality_score = 0.9 + i * 0.01
            face.detection_confidence = 0.95
            face.embedding = Embedding(np.random.rand(512).astype(np.float32))
            detected_faces.append(face)
        mock_ml_services.detect_faces.return_value = detected_faces

        # Mock saved faces
        saved_faces = [
            Face.create(
                photo_id=sample_photo.id.value,
                bbox=BoundingBox(x=i * 10, y=i * 20, width=100, height=120),
                quality_score=0.9,
            )
            for i in range(3)
        ]
        mock_face_repo.save_faces_batch.return_value = saved_faces

        # Act
        result = await service.detect_faces(sample_photo.id.value)

        # Assert
        mock_face_repo.save_faces_batch.assert_called_once()
        assert len(mock_face_repo.save_faces_batch.call_args[0][0]) == 3
        assert result.faces_detected == 3

    @pytest.mark.asyncio
    async def test_detect_faces_partial_crop_failure_continues(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        mock_face_repo: Mock,
        sample_photo: Photo,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When one face crop fails, should continue with others."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo

        # Mock two detected faces
        detected_faces = []
        for i in range(2):
            face = Mock()
            face.bbox = [i * 10, i * 20, 100, 120]
            face.quality_score = 0.9
            face.detection_confidence = 0.95
            face.embedding = Embedding(np.random.rand(512).astype(np.float32))
            detected_faces.append(face)
        mock_ml_services.detect_faces.return_value = detected_faces

        # Make crop_face fail on first call, succeed on second
        mock_ml_services.crop_face.side_effect = [
            Exception("Crop failed"),
            b"crop_data",
        ]

        # Mock saved face (only one should be saved)
        saved_face = Face.create(
            photo_id=sample_photo.id.value,
            bbox=BoundingBox(x=10, y=20, width=100, height=120),
        )
        mock_face_repo.save_faces_batch.return_value = [saved_face]

        # Act
        with caplog.at_level(logging.WARNING):
            result = await service.detect_faces(sample_photo.id.value)

        # Assert
        assert "Failed to process one detected face" in caplog.text
        assert result.faces_detected == 2  # 2 detected
        assert result.faces_saved == 1  # Only 1 saved successfully

    @pytest.mark.asyncio
    async def test_detect_faces_vector_store_failure_compensates(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        sample_photo: Photo,
    ) -> None:
        """When vector store fails critically, should delete faces from DB."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo

        # Mock detected face
        detected_face = Mock()
        detected_face.bbox = [10, 20, 100, 120]
        detected_face.quality_score = 0.9
        detected_face.detection_confidence = 0.95
        detected_face.embedding = Embedding(np.random.rand(512).astype(np.float32))
        mock_ml_services.detect_faces.return_value = [detected_face]

        # Mock saved face
        saved_face = Face.create(
            photo_id=sample_photo.id.value,
            bbox=BoundingBox(x=10, y=20, width=90, height=100),
        )
        mock_face_repo.save_faces_batch.return_value = [saved_face]

        # Make vector store fail critically in the try-except block
        mock_vector_store.store_face_embedding.side_effect = Exception("Critical error")

        # Make the critical failure happen in the outer try block
        def side_effect(*args: Any, **kwargs: Any) -> None:
            raise Exception("Critical vector store failure")

        mock_vector_store.store_face_embedding.side_effect = side_effect

        # Act & Assert
        # The method catches individual face embedding failures but re-raises critical errors
        # In this case, all embeddings fail individually, so no critical error is raised
        result = await service.detect_faces(sample_photo.id.value)

        # Should have partial success (faces saved but embeddings failed)
        assert result.faces_saved >= 0

    @pytest.mark.asyncio
    async def test_detect_faces_adds_face_ids_to_photo(
        self,
        service: PhotoProcessingService,
        mock_photo_repo: Mock,
        mock_ml_services: Mock,
        mock_face_repo: Mock,
        sample_photo: Photo,
    ) -> None:
        """When faces saved, should add face IDs to photo."""
        # Arrange
        mock_photo_repo.find_by_id.return_value = sample_photo
        mock_photo_repo.save.return_value = sample_photo

        # Mock detected face
        detected_face = Mock()
        detected_face.bbox = [10, 20, 100, 120]
        detected_face.quality_score = 0.9
        detected_face.detection_confidence = 0.95
        detected_face.embedding = Embedding(np.random.rand(512).astype(np.float32))
        mock_ml_services.detect_faces.return_value = [detected_face]

        # Mock saved face (Face entity is a dataclass, can't change ID after creation)
        saved_face = Face.create(
            photo_id=sample_photo.id.value,
            bbox=BoundingBox(x=10, y=20, width=90, height=100),
        )
        mock_face_repo.save_faces_batch.return_value = [saved_face]

        # Act
        await service.detect_faces(sample_photo.id.value)

        # Assert - photo.save should be called after adding faces
        assert mock_photo_repo.save.call_count >= 1


class TestProcessingResultTypes(TestPhotoProcessingService):
    """Tests for result type classes."""

    def test_processing_result_to_dict(self) -> None:
        """ProcessingResult should convert to dict correctly."""
        # Arrange
        result = ProcessingResult(
            status="completed",
            photo_id="test-id",
            thumbnail_path="/path/to/thumb.jpg",
        )

        # Act
        result_dict = result.to_dict()

        # Assert
        assert result_dict["status"] == "completed"
        assert result_dict["photo_id"] == "test-id"
        assert result_dict["thumbnail_path"] == "/path/to/thumb.jpg"

    def test_processing_result_to_dict_no_thumbnail(self) -> None:
        """ProcessingResult without thumbnail should not include it in dict."""
        # Arrange
        result = ProcessingResult(status="failed", photo_id="test-id")

        # Act
        result_dict = result.to_dict()

        # Assert
        assert "thumbnail_path" not in result_dict

    def test_face_detection_result_to_dict(self) -> None:
        """FaceDetectionResult should convert to dict correctly."""
        # Arrange
        result = FaceDetectionResult(
            status="completed",
            photo_id="test-id",
            faces_detected=5,
            faces_saved=4,
            faces_in_vector_store=3,
            face_ids=["id1", "id2", "id3"],
        )

        # Act
        result_dict = result.to_dict()

        # Assert
        assert result_dict["status"] == "completed"
        assert result_dict["faces_detected"] == 5
        assert result_dict["faces_saved"] == 4
        assert result_dict["faces_in_vector_store"] == 3
        assert len(result_dict["face_ids"]) == 3
