"""Unit tests for SearchService with focus on semantic search and filtering."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from app.application.ports.inbound.search_use_cases import (
    SearchFilters,
    SearchResponse,
    SearchResult,
)
from app.application.ports.outbound import (
    FaceRepository,
    MLServices,
    PhotoRepository,
    VectorStore,
)
from app.application.services.search_service import SearchService
from app.domain.entities import Photo
from app.domain.value_objects import PhotoId, SceneClassification


class BaseSearchServiceTest:
    """Base test class with common fixtures for SearchService tests."""

    @pytest.fixture
    def mock_photo_repo(self) -> Mock:
        """Mock photo repository."""
        repo = Mock(spec=PhotoRepository)
        repo.find_by_id = AsyncMock()
        repo.find_all = AsyncMock()
        return repo

    @pytest.fixture
    def mock_face_repo(self) -> Mock:
        """Mock face repository."""
        return Mock(spec=FaceRepository)

    @pytest.fixture
    def mock_vector_store(self) -> Mock:
        """Mock vector store."""
        store = Mock(spec=VectorStore)
        store.search_photos = AsyncMock()
        store.search_faces = AsyncMock()
        store.get_photo_embedding = AsyncMock()
        return store

    @pytest.fixture
    def mock_ml_services(self) -> Mock:
        """Mock ML services."""
        service = Mock(spec=MLServices)
        service.encode_text = AsyncMock()
        service.detect_faces = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_photo_repo: Mock,
        mock_face_repo: Mock,
        mock_vector_store: Mock,
        mock_ml_services: Mock,
    ) -> SearchService:
        """Create SearchService with mocked dependencies."""
        return SearchService(
            mock_photo_repo,
            mock_face_repo,
            mock_vector_store,
            mock_ml_services,
        )

    @staticmethod
    def create_sample_photo(
        photo_id: UUID | None = None,
        filename: str = "test.jpg",
        album_ids: list[UUID] | None = None,
        taken_at: datetime | None = None,
        has_faces: bool = False,
        is_indoor: bool | None = None,
        description: str | None = None,
        processing_status: str = "completed",
    ) -> Photo:
        """Create a sample photo for testing."""
        if photo_id is None:
            photo_id = uuid4()

        photo = Photo(
            id=PhotoId(photo_id),
            filename=filename,
            created_at=datetime.now(timezone.utc),
            album_ids=album_ids or [],
            taken_at=taken_at,
            face_ids=[uuid4()] if has_faces else [],
            description=description,
            processing_status=processing_status,
        )

        if is_indoor is not None:
            if is_indoor:
                photo.scene_classification = SceneClassification.indoor("office", confidence=0.95)
            else:
                photo.scene_classification = SceneClassification.outdoor("beach", confidence=0.95)

        return photo


class TestSemanticSearch(BaseSearchServiceTest):
    """Tests for semantic_search operation."""

    @pytest.mark.asyncio
    async def test_semantic_search_basic_query(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When searching with text query, should encode and search vector store."""
        # Arrange
        query = "sunset beach"
        embedding = [0.1, 0.2, 0.3]

        photo1 = self.create_sample_photo()
        photo2 = self.create_sample_photo()

        mock_ml_services.encode_text.return_value = embedding

        vector_result1 = Mock(id=photo1.id.value, score=0.95)
        vector_result2 = Mock(id=photo2.id.value, score=0.87)

        mock_vector_store.search_photos.return_value = [
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [photo1, photo2]

        # Act
        result = await service.semantic_search(query)

        # Assert
        assert len(result.results) == 2
        assert result.results[0].photo.id.value == photo1.id.value
        assert result.results[0].score == 0.95
        assert result.results[1].photo.id.value == photo2.id.value
        mock_ml_services.encode_text.assert_called_once_with(query)
        mock_vector_store.search_photos.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_search_with_limit_and_offset(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When searching with limit and offset, should apply pagination."""
        # Arrange
        query = "mountains"
        embedding = [0.1, 0.2, 0.3]
        limit = 10
        offset = 5

        photos = [self.create_sample_photo() for _ in range(15)]
        mock_ml_services.encode_text.return_value = embedding

        vector_results = [Mock(id=p.id.value, score=0.9 - i * 0.01) for i, p in enumerate(photos)]
        mock_vector_store.search_photos.return_value = vector_results

        mock_photo_repo.find_by_id.side_effect = photos

        # Act
        result = await service.semantic_search(query, limit=limit, offset=offset)

        # Assert
        # Should fetch limit + offset results from vector store
        call_args = mock_vector_store.search_photos.call_args
        assert call_args[1]["limit"] == limit + offset
        # Results should be offset and limited
        assert len(result.results) == limit

    @pytest.mark.asyncio
    async def test_semantic_search_with_album_filter(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When filtering by album, should pass filter to vector store."""
        # Arrange
        query = "vacation"
        album_id = uuid4()
        embedding = [0.1, 0.2, 0.3]

        photo1 = self.create_sample_photo(album_ids=[album_id])
        photo2 = self.create_sample_photo(album_ids=[album_id])

        mock_ml_services.encode_text.return_value = embedding

        vector_result1 = Mock(id=photo1.id.value, score=0.95)
        vector_result2 = Mock(id=photo2.id.value, score=0.87)

        mock_vector_store.search_photos.return_value = [
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [photo1, photo2]

        filters = SearchFilters(album_ids=[album_id])

        # Act
        result = await service.semantic_search(query, filters=filters)

        # Assert
        assert len(result.results) == 2
        # Verify qdrant filters were built
        call_kwargs = mock_vector_store.search_photos.call_kwargs
        assert call_kwargs["filters"] is not None

    @pytest.mark.asyncio
    async def test_semantic_search_filters_by_date_range(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When filtering by date range, should exclude photos outside range."""
        # Arrange
        query = "winter"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        embedding = [0.1, 0.2, 0.3]

        # Photo within range
        photo_in_range = self.create_sample_photo(
            taken_at=datetime(2023, 6, 15, tzinfo=timezone.utc)
        )

        # Photo outside range
        photo_outside_range = self.create_sample_photo(
            taken_at=datetime(2024, 6, 15, tzinfo=timezone.utc)
        )

        mock_ml_services.encode_text.return_value = embedding

        vector_result1 = Mock(id=photo_in_range.id.value, score=0.95)
        vector_result2 = Mock(id=photo_outside_range.id.value, score=0.87)

        mock_vector_store.search_photos.return_value = [
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [
            photo_in_range,
            photo_outside_range,
        ]

        filters = SearchFilters(start_date=start_date, end_date=end_date)

        # Act
        result = await service.semantic_search(query, filters=filters)

        # Assert - only photo in range should be returned
        assert len(result.results) == 1
        assert result.results[0].photo.id.value == photo_in_range.id.value

    @pytest.mark.asyncio
    async def test_semantic_search_filters_by_has_faces(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When filtering by has_faces, should exclude photos without faces."""
        # Arrange
        query = "people"
        embedding = [0.1, 0.2, 0.3]

        photo_with_faces = self.create_sample_photo(has_faces=True)
        photo_without_faces = self.create_sample_photo(has_faces=False)

        mock_ml_services.encode_text.return_value = embedding

        vector_result1 = Mock(id=photo_with_faces.id.value, score=0.95)
        vector_result2 = Mock(id=photo_without_faces.id.value, score=0.87)

        mock_vector_store.search_photos.return_value = [
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [
            photo_with_faces,
            photo_without_faces,
        ]

        filters = SearchFilters(has_faces=True)

        # Act
        result = await service.semantic_search(query, filters=filters)

        # Assert
        assert len(result.results) == 1
        assert len(result.results[0].photo.face_ids) > 0

    @pytest.mark.asyncio
    async def test_semantic_search_filters_by_indoor_outdoor(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When filtering by is_indoor, should exclude opposite scene type."""
        # Arrange
        query = "indoor office"
        embedding = [0.1, 0.2, 0.3]

        indoor_photo = self.create_sample_photo(is_indoor=True)
        outdoor_photo = self.create_sample_photo(is_indoor=False)

        mock_ml_services.encode_text.return_value = embedding

        vector_result1 = Mock(id=indoor_photo.id.value, score=0.95)
        vector_result2 = Mock(id=outdoor_photo.id.value, score=0.87)

        mock_vector_store.search_photos.return_value = [
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [indoor_photo, outdoor_photo]

        filters = SearchFilters(is_indoor=True)

        # Act
        result = await service.semantic_search(query, filters=filters)

        # Assert
        assert len(result.results) == 1
        assert result.results[0].photo.is_indoor is True

    @pytest.mark.asyncio
    async def test_semantic_search_empty_results(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
    ) -> None:
        """When no results found, should return empty response."""
        # Arrange
        query = "nonexistent"
        embedding = [0.1, 0.2, 0.3]

        mock_ml_services.encode_text.return_value = embedding
        mock_vector_store.search_photos.return_value = []

        # Act
        result = await service.semantic_search(query)

        # Assert
        assert len(result.results) == 0
        assert result.total == 0
        assert result.query_time_ms > 0

    @pytest.mark.asyncio
    async def test_semantic_search_missing_photo_in_db(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When vector store result not in DB, should skip it."""
        # Arrange
        query = "test"
        embedding = [0.1, 0.2, 0.3]

        photo = self.create_sample_photo()

        mock_ml_services.encode_text.return_value = embedding

        vector_result1 = Mock(id=uuid4(), score=0.95)  # Not in DB
        vector_result2 = Mock(id=photo.id.value, score=0.87)

        mock_vector_store.search_photos.return_value = [
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [None, photo]

        # Act
        result = await service.semantic_search(query)

        # Assert
        assert len(result.results) == 1
        assert result.results[0].photo.id.value == photo.id.value


class TestFindSimilar(BaseSearchServiceTest):
    """Tests for find_similar operation."""

    @pytest.mark.asyncio
    async def test_find_similar_returns_similar_photos(
        self,
        service: SearchService,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When finding similar photos, should exclude query photo."""
        # Arrange
        query_photo_id = uuid4()
        embedding = [0.1, 0.2, 0.3]

        similar_photo1 = self.create_sample_photo()
        similar_photo2 = self.create_sample_photo()

        mock_vector_store.get_photo_embedding.return_value = embedding

        vector_result0 = Mock(id=query_photo_id, score=1.0)  # Query photo
        vector_result1 = Mock(id=similar_photo1.id.value, score=0.95)
        vector_result2 = Mock(id=similar_photo2.id.value, score=0.87)

        mock_vector_store.search_photos.return_value = [
            vector_result0,
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [
            similar_photo1,
            similar_photo2,
        ]

        # Act
        result = await service.find_similar(query_photo_id, limit=10)

        # Assert
        assert len(result) == 2
        # Query photo should not be in results
        assert all(r.photo.id.value != query_photo_id for r in result)
        assert result[0].photo.id.value == similar_photo1.id.value

    @pytest.mark.asyncio
    async def test_find_similar_respects_limit(
        self,
        service: SearchService,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When finding similar photos, should respect limit."""
        # Arrange
        query_photo_id = uuid4()
        embedding = [0.1, 0.2, 0.3]
        limit = 5

        photos = [self.create_sample_photo() for _ in range(10)]

        mock_vector_store.get_photo_embedding.return_value = embedding

        vector_results = [
            Mock(id=query_photo_id, score=1.0),  # Query photo
            *[Mock(id=p.id.value, score=0.9 - i * 0.01) for i, p in enumerate(photos)],
        ]

        mock_vector_store.search_photos.return_value = vector_results
        mock_photo_repo.find_by_id.side_effect = photos

        # Act
        result = await service.find_similar(query_photo_id, limit=limit)

        # Assert
        assert len(result) <= limit

    @pytest.mark.asyncio
    async def test_find_similar_no_embedding(
        self,
        service: SearchService,
        mock_vector_store: Mock,
    ) -> None:
        """When photo has no embedding, should return empty results."""
        # Arrange
        query_photo_id = uuid4()
        mock_vector_store.get_photo_embedding.return_value = None

        # Act
        result = await service.find_similar(query_photo_id)

        # Assert
        assert len(result) == 0


class TestSearchByFace(BaseSearchServiceTest):
    """Tests for search_by_face operation."""

    @pytest.mark.asyncio
    async def test_search_by_face_finds_similar_faces(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When searching by face, should find photos with similar faces."""
        # Arrange
        face_image = b"fake image data"
        embedding = [0.1, 0.2, 0.3]

        photo1 = self.create_sample_photo()
        photo2 = self.create_sample_photo()

        detected_face = Mock(embedding=embedding)
        mock_ml_services.detect_faces.return_value = [detected_face]

        vector_result1 = Mock(
            id=uuid4(),
            score=0.95,
            payload={"photo_id": str(photo1.id.value)},
        )
        vector_result2 = Mock(
            id=uuid4(),
            score=0.87,
            payload={"photo_id": str(photo2.id.value)},
        )

        mock_vector_store.search_faces.return_value = [
            vector_result1,
            vector_result2,
        ]
        mock_photo_repo.find_by_id.side_effect = [photo1, photo2]

        # Act
        result = await service.search_by_face(face_image, limit=20)

        # Assert
        assert len(result) == 2
        assert result[0].photo.id.value == photo1.id.value
        mock_ml_services.detect_faces.assert_called_once_with(face_image)

    @pytest.mark.asyncio
    async def test_search_by_face_no_faces_detected(
        self,
        service: SearchService,
        mock_ml_services: Mock,
    ) -> None:
        """When no faces detected in image, should return empty results."""
        # Arrange
        face_image = b"fake image data"
        mock_ml_services.detect_faces.return_value = []

        # Act
        result = await service.search_by_face(face_image)

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_by_face_deduplicates_by_photo(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When multiple faces in same photo, should deduplicate by photo ID."""
        # Arrange
        face_image = b"fake image data"
        embedding = [0.1, 0.2, 0.3]
        photo_id = uuid4()

        photo = self.create_sample_photo()

        detected_face = Mock(embedding=embedding)
        mock_ml_services.detect_faces.return_value = [detected_face]

        # Multiple face results from same photo
        vector_result1 = Mock(
            id=uuid4(),
            score=0.95,
            payload={"photo_id": str(photo.id.value)},
        )
        vector_result2 = Mock(
            id=uuid4(),
            score=0.93,
            payload={"photo_id": str(photo.id.value)},
        )
        vector_result3 = Mock(
            id=uuid4(),
            score=0.91,
            payload={"photo_id": str(uuid4())},
        )

        mock_vector_store.search_faces.return_value = [
            vector_result1,
            vector_result2,
            vector_result3,
        ]
        mock_photo_repo.find_by_id.side_effect = [photo, photo, photo]

        # Act
        result = await service.search_by_face(face_image, limit=20)

        # Assert
        # Should have at most 2 unique photos despite 3 faces found
        photo_ids_in_results = {r.photo.id.value for r in result}
        assert len(photo_ids_in_results) <= 2


class TestFilteringHelpers(BaseSearchServiceTest):
    """Tests for internal filtering helper methods."""

    @pytest.mark.asyncio
    async def test_passes_filters_checks_description(
        self,
        service: SearchService,
    ) -> None:
        """When filtering by has_description, should check description field."""
        # Arrange
        photo_with_desc = self.create_sample_photo(description="A beautiful sunset")
        photo_without_desc = self.create_sample_photo(description=None)

        filters = SearchFilters(has_description=True)

        # Act & Assert
        assert service._passes_filters(photo_with_desc, filters)
        assert not service._passes_filters(photo_without_desc, filters)

    @pytest.mark.asyncio
    async def test_passes_filters_checks_processing_status(
        self,
        service: SearchService,
    ) -> None:
        """When filtering by processing_status, should check photo status."""
        # Arrange
        completed_photo = self.create_sample_photo(processing_status="completed")
        pending_photo = self.create_sample_photo(processing_status="pending")

        filters = SearchFilters(processing_status="completed")

        # Act & Assert
        assert service._passes_filters(completed_photo, filters)
        assert not service._passes_filters(pending_photo, filters)

    def test_build_qdrant_filters_includes_album_ids(
        self,
        service: SearchService,
    ) -> None:
        """When building filters, should include album IDs."""
        # Arrange
        album_id1 = uuid4()
        album_id2 = uuid4()
        filters = SearchFilters(album_ids=[album_id1, album_id2])

        # Act
        result = service._build_qdrant_filters(filters)

        # Assert
        assert "album_id" in result
        assert result["album_id"] == [str(album_id1), str(album_id2)]

    def test_build_qdrant_filters_includes_connector_ids(
        self,
        service: SearchService,
    ) -> None:
        """When building filters, should include connector IDs."""
        # Arrange
        connector_id1 = uuid4()
        connector_id2 = uuid4()
        filters = SearchFilters(connector_ids=[connector_id1, connector_id2])

        # Act
        result = service._build_qdrant_filters(filters)

        # Assert
        assert "connector_id" in result
        assert result["connector_id"] == [str(connector_id1), str(connector_id2)]


class TestCombinedSearch(BaseSearchServiceTest):
    """Tests for search_combined operation."""

    @pytest.mark.asyncio
    async def test_search_combined_with_query_delegates_to_semantic_search(
        self,
        service: SearchService,
        mock_ml_services: Mock,
        mock_vector_store: Mock,
        mock_photo_repo: Mock,
    ) -> None:
        """When query provided, should use semantic search."""
        # Arrange
        query = "beach"
        embedding = [0.1, 0.2, 0.3]

        photo = self.create_sample_photo()

        mock_ml_services.encode_text.return_value = embedding

        vector_result = Mock(id=photo.id.value, score=0.95)
        mock_vector_store.search_photos.return_value = [vector_result]
        mock_photo_repo.find_by_id.return_value = photo

        # Act
        result = await service.search_combined(query=query)

        # Assert
        assert len(result.results) == 1
        mock_ml_services.encode_text.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_search_combined_without_query_returns_filtered_results(
        self,
        service: SearchService,
        mock_photo_repo: Mock,
    ) -> None:
        """When no query provided, should return all photos with filters applied."""
        # Arrange
        photos = [
            self.create_sample_photo(is_indoor=True),
            self.create_sample_photo(is_indoor=False),
        ]
        mock_photo_repo.find_all.return_value = photos

        filters = SearchFilters(is_indoor=True)

        # Act
        result = await service.search_combined(filters=filters)

        # Assert
        assert len(result.results) == 1
        assert result.results[0].photo.is_indoor is True

    @pytest.mark.asyncio
    async def test_search_combined_sorts_by_date(
        self,
        service: SearchService,
        mock_photo_repo: Mock,
    ) -> None:
        """When sorting by date, should order results chronologically."""
        # Arrange
        photo1 = self.create_sample_photo(
            taken_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        photo2 = self.create_sample_photo(
            taken_at=datetime(2024, 1, 5, tzinfo=timezone.utc)
        )
        photo3 = self.create_sample_photo(
            taken_at=datetime(2024, 1, 10, tzinfo=timezone.utc)
        )

        # Return in random order
        mock_photo_repo.find_all.return_value = [photo3, photo1, photo2]

        # Act
        result = await service.search_combined(sort_by="date_asc")

        # Assert
        assert result.results[0].photo.id.value == photo1.id.value
        assert result.results[1].photo.id.value == photo2.id.value
        assert result.results[2].photo.id.value == photo3.id.value

    @pytest.mark.asyncio
    async def test_search_combined_respects_limit_and_offset(
        self,
        service: SearchService,
        mock_photo_repo: Mock,
    ) -> None:
        """When filtering without query, should apply limit and offset."""
        # Arrange
        photos = [self.create_sample_photo() for _ in range(30)]
        mock_photo_repo.find_all.return_value = photos

        # Act
        result = await service.search_combined(limit=10, offset=5)

        # Assert
        assert len(result.results) == 10
