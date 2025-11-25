"""Integration tests for search API endpoints.

Tests the following endpoints:
- POST /api/v1/search - Semantic search with request body
- GET /api/v1/search - Semantic search with query parameters

These tests would have caught the bug where GET endpoint wasn't passing dependencies.

Following TDD approach - comprehensive API tests for search functionality.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from httpx import AsyncClient

from app.domain.entities.connector import Connector, ConnectorType
from app.domain.entities.photo import Photo
from tests.integration.factories import PhotoFactory, ConnectorFactory, EmbeddingFactory


class TestSearchPostEndpoint:
    """Tests for POST /api/v1/search."""

    @pytest.mark.asyncio
    async def test_post_search_basic_query(
        self, client: AsyncClient, photo_repo, connector_repo, test_vector_store
    ):
        """Should perform semantic search with basic query."""
        # Given: indexed photos
        connector = ConnectorFactory.create_local_folder()
        saved_connector = await connector_repo.save(connector)

        photos = []
        for i in range(3):
            photo = PhotoFactory.create(
                filename=f"sunset_{i}.jpg",
                description="Beautiful sunset",
                connector_id=saved_connector.id.value,
            )
            saved_photo = await photo_repo.save(photo)
            photos.append(saved_photo)

            # Index in vector store
            embedding = EmbeddingFactory.create_clip_embedding()
            await test_vector_store.store_photo_embedding(
                saved_photo.id.value,
                embedding,
            )

        # When: POST search
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "sunset over mountains",
                "limit": 10,
                "offset": 0,
            }
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert "results" in data["data"]
        assert "meta" in data
        assert data["meta"]["limit"] == 10
        assert data["meta"]["offset"] == 0

    @pytest.mark.asyncio
    async def test_post_search_returns_photo_metadata(
        self, client: AsyncClient, photo_repo, test_vector_store, base_embedding, setup_search_mocks
    ):
        """Should return complete photo metadata in results."""
        # Given: indexed photo with full metadata
        photo = PhotoFactory.create(
            filename="photo.jpg",
            description="Test photo",
            width=1920,
            height=1080,
            mime_type="image/jpeg",
        )
        saved_photo = await photo_repo.save(photo)

        # Use a similar embedding to base_embedding so search will find it
        await test_vector_store.store_photo_embedding(
            saved_photo.id.value,
            EmbeddingFactory.create_similar_embedding(base_embedding, noise=0.01),
        )

        # When
        response = await client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 10}
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        results = data["data"]["results"]
        assert len(results) >= 1

        result = results[0]
        assert "photo" in result
        assert "score" in result
        assert "highlights" in result

        photo_data = result["photo"]
        assert photo_data["id"] == str(saved_photo.id.value)
        assert photo_data["filename"] == "photo.jpg"
        assert photo_data["mime_type"] == "image/jpeg"
        assert photo_data["width"] == 1920
        assert photo_data["height"] == 1080

    @pytest.mark.asyncio
    async def test_post_search_with_connector_filter(
        self, client: AsyncClient, photo_repo, connector_repo, test_vector_store
    ):
        """Should filter results by connector ID."""
        # Given: photos from two different connectors
        connector1 = ConnectorFactory.create_local_folder(name="Connector 1")
        connector2 = ConnectorFactory.create_local_folder(name="Connector 2")
        saved_c1 = await connector_repo.save(connector1)
        saved_c2 = await connector_repo.save(connector2)

        base_embedding = EmbeddingFactory.create_clip_embedding()

        # Create photos for connector 1
        c1_photos = []
        for i in range(2):
            photo = PhotoFactory.create(
                filename=f"c1_photo_{i}.jpg",
                connector_id=saved_c1.id.value,
            )
            saved = await photo_repo.save(photo)
            c1_photos.append(saved)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                EmbeddingFactory.create_similar_embedding(base_embedding),
            )

        # Create photos for connector 2
        c2_photos = []
        for i in range(2):
            photo = PhotoFactory.create(
                filename=f"c2_photo_{i}.jpg",
                connector_id=saved_c2.id.value,
            )
            saved = await photo_repo.save(photo)
            c2_photos.append(saved)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                EmbeddingFactory.create_similar_embedding(base_embedding),
            )

        # When: search with connector filter
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "test",
                "limit": 10,
                "filters": {
                    "connector_ids": [str(saved_c1.id.value)]
                }
            }
        )

        # Then: only connector 1 photos returned
        assert response.status_code == 200
        data = response.json()

        results = data["data"]["results"]
        result_ids = {r["photo"]["id"] for r in results}
        c1_ids = {str(p.id.value) for p in c1_photos}
        c2_ids = {str(p.id.value) for p in c2_photos}

        # All results should be from connector 1
        assert result_ids.issubset(c1_ids)
        # No results from connector 2
        assert len(result_ids.intersection(c2_ids)) == 0

    @pytest.mark.asyncio
    async def test_post_search_with_pagination(
        self, client: AsyncClient, photo_repo, test_vector_store, base_embedding, setup_search_mocks
    ):
        """Should respect limit and offset parameters."""
        # Given: 10 indexed photos with similar embeddings
        for i in range(10):
            photo = PhotoFactory.create(filename=f"photo_{i}.jpg")
            saved = await photo_repo.save(photo)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                EmbeddingFactory.create_similar_embedding(base_embedding, noise=0.01),
            )

        # When: page 1 (limit=5, offset=0)
        response1 = await client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 5, "offset": 0}
        )

        # Then
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1["data"]["results"]) == 5
        assert page1["meta"]["limit"] == 5
        assert page1["meta"]["offset"] == 0

        # When: page 2 (limit=5, offset=5)
        response2 = await client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 5, "offset": 5}
        )

        # Then
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2["data"]["results"]) == 5

        # No overlap between pages
        page1_ids = {r["photo"]["id"] for r in page1["data"]["results"]}
        page2_ids = {r["photo"]["id"] for r in page2["data"]["results"]}
        assert len(page1_ids.intersection(page2_ids)) == 0

    @pytest.mark.asyncio
    async def test_post_search_empty_results(
        self, client: AsyncClient, test_vector_store
    ):
        """Should handle no results gracefully."""
        # When: search with no indexed photos
        response = await client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 10}
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["results"] == []
        assert data["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_post_search_invalid_query_empty(
        self, client: AsyncClient
    ):
        """Should reject empty query."""
        # When
        response = await client.post(
            "/api/v1/search",
            json={"query": "", "limit": 10}
        )

        # Then: validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_search_invalid_query_too_long(
        self, client: AsyncClient
    ):
        """Should reject query exceeding max length."""
        # When: query > 500 characters
        long_query = "a" * 501
        response = await client.post(
            "/api/v1/search",
            json={"query": long_query, "limit": 10}
        )

        # Then: validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_search_timing_info(
        self, client: AsyncClient, photo_repo, test_vector_store
    ):
        """Should return timing information for performance monitoring."""
        # Given: indexed photo
        photo = PhotoFactory.create()
        saved = await photo_repo.save(photo)

        embedding = EmbeddingFactory.create_clip_embedding()
        await test_vector_store.store_photo_embedding(saved.id.value, embedding)

        # When
        response = await client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 10}
        )

        # Then: timing info included
        assert response.status_code == 200
        data = response.json()

        assert "query_embedding_time_ms" in data["data"]
        assert "search_time_ms" in data["data"]
        assert isinstance(data["data"]["query_embedding_time_ms"], (int, float))
        assert isinstance(data["data"]["search_time_ms"], (int, float))


class TestSearchGetEndpoint:
    """Tests for GET /api/v1/search.

    CRITICAL: These tests specifically verify that the GET endpoint
    properly passes dependencies to the POST handler, which was the bug.
    """

    @pytest.mark.asyncio
    async def test_get_search_basic_query(
        self, client: AsyncClient, photo_repo, test_vector_store
    ):
        """Should perform semantic search via GET request.

        This test would have caught the bug where GET wasn't passing dependencies.
        """
        # Given: indexed photo
        photo = PhotoFactory.create(filename="sunset.jpg")
        saved = await photo_repo.save(photo)

        embedding = EmbeddingFactory.create_clip_embedding()
        await test_vector_store.store_photo_embedding(saved.id.value, embedding)

        # When: GET search with query parameter
        response = await client.get(
            "/api/v1/search?q=sunset"
        )

        # Then: should work without errors (bug would cause 500 error)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert "results" in data["data"]

    @pytest.mark.asyncio
    async def test_get_search_with_all_parameters(
        self, client: AsyncClient, photo_repo, connector_repo, test_vector_store
    ):
        """Should support all query parameters including filters."""
        # Given: photos with connector
        connector = ConnectorFactory.create_local_folder()
        saved_connector = await connector_repo.save(connector)

        base_embedding = EmbeddingFactory.create_clip_embedding()

        for i in range(10):
            photo = PhotoFactory.create(
                filename=f"photo_{i}.jpg",
                connector_id=saved_connector.id.value,
            )
            saved = await photo_repo.save(photo)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                EmbeddingFactory.create_similar_embedding(base_embedding),
            )

        # When: GET with all parameters
        response = await client.get(
            f"/api/v1/search?q=test&limit=5&offset=2&connector_id={saved_connector.id.value}"
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["meta"]["limit"] == 5
        assert data["meta"]["offset"] == 2

        # Verify connector filter was applied
        results = data["data"]["results"]
        for result in results:
            assert result["photo"]["connector_id"] == str(saved_connector.id.value)

    @pytest.mark.asyncio
    async def test_get_search_pagination(
        self, client: AsyncClient, photo_repo, test_vector_store, base_embedding, setup_search_mocks
    ):
        """Should handle pagination correctly via GET."""
        # Given: 10 indexed photos with similar embeddings
        for i in range(10):
            photo = PhotoFactory.create(filename=f"photo_{i}.jpg")
            saved = await photo_repo.save(photo)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                EmbeddingFactory.create_similar_embedding(base_embedding, noise=0.01),
            )

        # When: page 1
        response1 = await client.get("/api/v1/search?q=test&limit=3&offset=0")

        # Then
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1["data"]["results"]) == 3

        # When: page 2
        response2 = await client.get("/api/v1/search?q=test&limit=3&offset=3")

        # Then
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2["data"]["results"]) == 3

        # No overlap
        page1_ids = {r["photo"]["id"] for r in page1["data"]["results"]}
        page2_ids = {r["photo"]["id"] for r in page2["data"]["results"]}
        assert len(page1_ids.intersection(page2_ids)) == 0

    @pytest.mark.asyncio
    async def test_get_search_default_parameters(
        self, client: AsyncClient, photo_repo, test_vector_store, base_embedding, setup_search_mocks
    ):
        """Should use default limit and offset when not specified."""
        # Given: indexed photos with similar embeddings
        for i in range(25):
            photo = PhotoFactory.create(filename=f"photo_{i}.jpg")
            saved = await photo_repo.save(photo)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                EmbeddingFactory.create_similar_embedding(base_embedding, noise=0.01),
            )

        # When: no limit/offset specified
        response = await client.get("/api/v1/search?q=test")

        # Then: should use defaults (limit=20, offset=0)
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["limit"] == 20
        assert data["meta"]["offset"] == 0
        assert len(data["data"]["results"]) == 20

    @pytest.mark.asyncio
    async def test_get_search_missing_query_parameter(
        self, client: AsyncClient
    ):
        """Should reject request without query parameter."""
        # When: no 'q' parameter
        response = await client.get("/api/v1/search")

        # Then: validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_search_empty_query(
        self, client: AsyncClient
    ):
        """Should reject empty query string."""
        # When
        response = await client.get("/api/v1/search?q=")

        # Then: validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_search_query_too_long(
        self, client: AsyncClient
    ):
        """Should reject query exceeding max length."""
        # When: query > 500 characters
        long_query = "a" * 501
        response = await client.get(f"/api/v1/search?q={long_query}")

        # Then: validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_search_invalid_limit(
        self, client: AsyncClient
    ):
        """Should reject invalid limit values."""
        # When: limit > 100
        response1 = await client.get("/api/v1/search?q=test&limit=101")
        assert response1.status_code == 422

        # When: limit < 1
        response2 = await client.get("/api/v1/search?q=test&limit=0")
        assert response2.status_code == 422

    @pytest.mark.asyncio
    async def test_get_search_invalid_offset(
        self, client: AsyncClient
    ):
        """Should reject invalid offset values."""
        # When: negative offset
        response1 = await client.get("/api/v1/search?q=test&offset=-1")
        assert response1.status_code == 422

        # When: offset > 10000
        response2 = await client.get("/api/v1/search?q=test&offset=10001")
        assert response2.status_code == 422

    @pytest.mark.asyncio
    async def test_get_search_with_connector_filter(
        self, client: AsyncClient, photo_repo, connector_repo, test_vector_store
    ):
        """Should filter by connector_id parameter."""
        # Given: photos from different connectors
        connector1 = ConnectorFactory.create_local_folder()
        connector2 = ConnectorFactory.create_local_folder()
        saved_c1 = await connector_repo.save(connector1)
        saved_c2 = await connector_repo.save(connector2)

        base_embedding = EmbeddingFactory.create_clip_embedding()

        # Photos for connector 1
        photo1 = PhotoFactory.create(
            filename="c1.jpg",
            connector_id=saved_c1.id.value,
        )
        saved1 = await photo_repo.save(photo1)
        await test_vector_store.store_photo_embedding(
            saved1.id.value,
            EmbeddingFactory.create_similar_embedding(base_embedding),
        )

        # Photos for connector 2
        photo2 = PhotoFactory.create(
            filename="c2.jpg",
            connector_id=saved_c2.id.value,
        )
        saved2 = await photo_repo.save(photo2)
        await test_vector_store.store_photo_embedding(
            saved2.id.value,
            EmbeddingFactory.create_similar_embedding(base_embedding),
        )

        # When: filter by connector 1
        response = await client.get(
            f"/api/v1/search?q=test&connector_id={saved_c1.id.value}"
        )

        # Then: only connector 1 photos
        assert response.status_code == 200
        data = response.json()

        results = data["data"]["results"]
        for result in results:
            assert result["photo"]["connector_id"] == str(saved_c1.id.value)

    @pytest.mark.asyncio
    async def test_get_search_returns_same_results_as_post(
        self, client: AsyncClient, photo_repo, test_vector_store
    ):
        """GET and POST should return equivalent results for same query.

        This ensures GET endpoint properly delegates to POST handler.
        """
        # Given: indexed photos
        base_embedding = EmbeddingFactory.create_clip_embedding()

        for i in range(5):
            photo = PhotoFactory.create(filename=f"photo_{i}.jpg")
            saved = await photo_repo.save(photo)

            await test_vector_store.store_photo_embedding(
                saved.id.value,
                EmbeddingFactory.create_similar_embedding(base_embedding),
            )

        # When: search via GET
        get_response = await client.get("/api/v1/search?q=test&limit=5&offset=0")

        # When: search via POST with same parameters
        post_response = await client.post(
            "/api/v1/search",
            json={"query": "test", "limit": 5, "offset": 0}
        )

        # Then: both should succeed
        assert get_response.status_code == 200
        assert post_response.status_code == 200

        get_data = get_response.json()
        post_data = post_response.json()

        # Results should be equivalent
        assert get_data["success"] == post_data["success"]
        assert get_data["meta"] == post_data["meta"]

        # Result IDs should match (order might vary slightly due to timing)
        get_ids = {r["photo"]["id"] for r in get_data["data"]["results"]}
        post_ids = {r["photo"]["id"] for r in post_data["data"]["results"]}
        assert get_ids == post_ids


class TestSearchErrorHandling:
    """Tests for error handling in search endpoints."""

    @pytest.mark.asyncio
    async def test_search_handles_ml_service_error(
        self, client: AsyncClient, photo_repo, test_vector_store
    ):
        """Should handle ML service errors gracefully."""
        # Given: indexed photo
        photo = PhotoFactory.create()
        saved = await photo_repo.save(photo)

        embedding = EmbeddingFactory.create_clip_embedding()
        await test_vector_store.store_photo_embedding(saved.id.value, embedding)

        # When: ML service fails (mock this)
        with patch("app.adapters.outbound.ml.MLServicesAdapter.encode_text") as mock_encode:
            mock_encode.side_effect = Exception("ML service unavailable")

            response = await client.post(
                "/api/v1/search",
                json={"query": "test", "limit": 10}
            )

        # Then: error response
        assert response.status_code == 200  # Returns 200 with error in response
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert data["data"]["results"] == []

    @pytest.mark.asyncio
    async def test_search_handles_vector_store_error(
        self, client: AsyncClient, photo_repo, test_vector_store
    ):
        """Should handle vector store errors gracefully."""
        # Patch the vector store's search_photos method to raise an exception
        # We need to patch it at the module level where it's used
        with patch("app.adapters.outbound.persistence.qdrant.QdrantVectorStore.search_photos") as mock_search:
            mock_search.side_effect = Exception("Vector store unavailable")

            response = await client.post(
                "/api/v1/search",
                json={"query": "test", "limit": 10}
            )

        # Then: error response
        assert response.status_code == 200  # Returns 200 with error in response
        data = response.json()

        assert data["success"] is False
        assert "error" in data


# Fixtures

@pytest.fixture
async def photo_repo(db_session):
    """Provide PhotoRepository instance."""
    from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
        PhotoRepositoryPostgres,
    )
    return PhotoRepositoryPostgres(db_session)


@pytest.fixture
async def connector_repo(db_session):
    """Provide ConnectorRepository instance."""
    from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
        ConnectorRepositoryPostgres,
    )
    return ConnectorRepositoryPostgres(db_session)


@pytest.fixture
async def test_vector_store():
    """Create a test Qdrant vector store with unique collection."""
    from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
    from app.config import get_settings

    test_id = str(uuid4())[:8]
    photos_collection = f"test_search_photos_{test_id}"
    faces_collection = f"test_search_faces_{test_id}"

    settings = get_settings()
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        photos_collection=photos_collection,
        faces_collection=faces_collection,
    )

    yield vector_store

    # Cleanup: Delete test collections
    try:
        await vector_store._client.delete_collection(photos_collection)
    except Exception:
        pass

    try:
        await vector_store._client.delete_collection(faces_collection)
    except Exception:
        pass


@pytest.fixture
def base_embedding():
    """
    Provide a consistent base embedding for tests.

    This embedding is used both for storing test photo embeddings
    and for mocking the ML service's encode_text method.
    """
    return EmbeddingFactory.create_clip_embedding()


@pytest.fixture
async def setup_search_mocks(test_vector_store, base_embedding):
    """
    Set up mocks for search tests to ensure embeddings match.

    Overrides both the ML service to return predictable embeddings
    and the vector store to use the test instance.
    """
    from app.dependencies import get_ml_services, get_vector_store
    from app.main import app

    # Create mock ML service that returns base_embedding
    mock_ml_service = MagicMock()
    async def mock_encode_text(text: str):
        return base_embedding
    mock_ml_service.encode_text = mock_encode_text

    # Override dependencies
    app.dependency_overrides[get_ml_services] = lambda: mock_ml_service
    app.dependency_overrides[get_vector_store] = lambda: test_vector_store

    yield

    # Cleanup
    if get_ml_services in app.dependency_overrides:
        del app.dependency_overrides[get_ml_services]
    if get_vector_store in app.dependency_overrides:
        del app.dependency_overrides[get_vector_store]
