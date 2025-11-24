"""Unit tests for Qdrant VectorStore implementation."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.qdrant.vector_store import QdrantVectorStore
from app.application.ports.outbound.vector_store import VectorSearchResult
from app.domain.value_objects import Embedding


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    return MagicMock()


@pytest.fixture
def mock_async_qdrant_client():
    """Create a mock async Qdrant client."""
    return AsyncMock()


@pytest.fixture
def sample_embedding():
    """Create a sample embedding for testing."""
    return Embedding(values=[0.1, 0.2, 0.3] + [0.0] * 509)  # 512-dim


class TestQdrantVectorStoreInitialization:
    """Tests for QdrantVectorStore initialization."""

    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    def test_init_with_default_settings(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
    ):
        """When initializing without params, it should use settings."""
        # Mock settings
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        # Mock model config
        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        # Mock sync client methods
        mock_sync_client = MagicMock()
        mock_sync_client_class.return_value = mock_sync_client

        # Mock async client
        mock_async_client = AsyncMock()
        mock_async_client_class.return_value = mock_async_client

        # Reset global singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore()

        assert vector_store._url == "http://localhost:6333"
        assert vector_store._photos_collection == "photos"
        assert vector_store._faces_collection == "faces"
        assert vector_store._clip_embedding_dim == 512

        # Clean up singleton
        vs_module._async_client = None

    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    def test_init_with_custom_params(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
    ):
        """When initializing with custom params, they should be used."""
        # Mock settings (will be overridden)
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        # Mock model config
        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        # Mock clients
        mock_sync_client = MagicMock()
        mock_sync_client_class.return_value = mock_sync_client
        mock_async_client = AsyncMock()
        mock_async_client_class.return_value = mock_async_client

        # Reset singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore(
            url="http://custom:6333",
            photos_collection="custom_photos",
            faces_collection="custom_faces",
        )

        assert vector_store._url == "http://custom:6333"
        assert vector_store._photos_collection == "custom_photos"
        assert vector_store._faces_collection == "custom_faces"

        # Clean up
        vs_module._async_client = None

    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    def test_init_ensures_collections(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
    ):
        """When initializing, it should ensure collections exist."""
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        mock_sync_client = MagicMock()
        # Simulate collections don't exist
        mock_sync_client.get_collection.side_effect = Exception("Not found")
        mock_sync_client_class.return_value = mock_sync_client

        mock_async_client = AsyncMock()
        mock_async_client_class.return_value = mock_async_client

        # Reset singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore()

        # Should attempt to create collections
        assert mock_sync_client.create_collection.call_count == 2

        # Clean up
        vs_module._async_client = None


class TestQdrantVectorStorePhotoOperations:
    """Tests for photo embedding operations."""

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    async def test_store_photo_embedding(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
        sample_embedding,
    ):
        """When storing photo embedding, it should be upserted to collection."""
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        mock_sync_client = MagicMock()
        mock_sync_client_class.return_value = mock_sync_client

        mock_async_client = AsyncMock()
        mock_async_client_class.return_value = mock_async_client

        # Reset singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore()
        photo_id = uuid4()

        await vector_store.store_photo_embedding(
            photo_id=photo_id,
            embedding=sample_embedding,
            payload={"filename": "test.jpg"},
        )

        # Verify upsert was called
        mock_async_client.upsert.assert_called_once()
        call_args = mock_async_client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "photos"
        points = call_args.kwargs["points"]
        assert len(points) == 1
        assert points[0].id == str(photo_id)

        # Clean up
        vs_module._async_client = None

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    async def test_search_photos(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
        sample_embedding,
    ):
        """When searching photos, it should return search results."""
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        mock_sync_client = MagicMock()
        mock_sync_client_class.return_value = mock_sync_client

        mock_async_client = AsyncMock()
        # Mock search response
        photo1_id = uuid4()
        photo2_id = uuid4()
        mock_response = Mock()
        mock_response.points = [
            Mock(id=str(photo1_id), score=0.95, payload={"filename": "test1.jpg"}),
            Mock(id=str(photo2_id), score=0.87, payload={"filename": "test2.jpg"}),
        ]
        mock_async_client.query_points.return_value = mock_response
        mock_async_client_class.return_value = mock_async_client

        # Reset singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore()

        results = await vector_store.search_photos(
            query_embedding=sample_embedding,
            limit=10,
        )

        assert len(results) == 2
        assert isinstance(results[0], VectorSearchResult)
        assert results[0].id == photo1_id
        assert results[0].score == 0.95
        assert results[0].payload["filename"] == "test1.jpg"

        # Clean up
        vs_module._async_client = None

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    async def test_delete_photo_embedding_success(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
    ):
        """When deleting photo embedding, it should return True on success."""
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        mock_sync_client = MagicMock()
        mock_sync_client_class.return_value = mock_sync_client

        mock_async_client = AsyncMock()
        mock_async_client_class.return_value = mock_async_client

        # Reset singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore()
        photo_id = uuid4()

        result = await vector_store.delete_photo_embedding(photo_id)

        assert result is True
        mock_async_client.delete.assert_called_once()

        # Clean up
        vs_module._async_client = None

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    async def test_delete_photo_embedding_handles_error(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
    ):
        """When deletion fails, it should return False."""
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        mock_sync_client = MagicMock()
        mock_sync_client_class.return_value = mock_sync_client

        mock_async_client = AsyncMock()
        mock_async_client.delete.side_effect = Exception("Connection error")
        mock_async_client_class.return_value = mock_async_client

        # Reset singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore()
        photo_id = uuid4()

        result = await vector_store.delete_photo_embedding(photo_id)

        assert result is False

        # Clean up
        vs_module._async_client = None


class TestQdrantVectorStoreErrorHandling:
    """Tests for error handling in vector store operations."""

    @pytest.mark.asyncio
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.QdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.AsyncQdrantClient")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_settings")
    @patch("app.adapters.outbound.persistence.qdrant.vector_store.get_model_config")
    async def test_store_photo_embedding_propagates_errors(
        self,
        mock_get_model_config,
        mock_get_settings,
        mock_async_client_class,
        mock_sync_client_class,
        sample_embedding,
    ):
        """When upsert fails, error should be propagated."""
        mock_settings = Mock(
            qdrant_url="http://localhost:6333",
            qdrant_collection_photos="photos",
            qdrant_collection_faces="faces",
        )
        mock_get_settings.return_value = mock_settings

        mock_config = Mock()
        mock_config.clip.embedding_dim = 512
        mock_get_model_config.return_value = mock_config

        mock_sync_client = MagicMock()
        mock_sync_client_class.return_value = mock_sync_client

        mock_async_client = AsyncMock()
        mock_async_client.upsert.side_effect = Exception("Qdrant connection error")
        mock_async_client_class.return_value = mock_async_client

        # Reset singleton
        import app.adapters.outbound.persistence.qdrant.vector_store as vs_module

        vs_module._async_client = None

        vector_store = QdrantVectorStore()
        photo_id = uuid4()

        with pytest.raises(Exception) as exc:
            await vector_store.store_photo_embedding(
                photo_id=photo_id,
                embedding=sample_embedding,
            )

        assert "Qdrant connection error" in str(exc.value)

        # Clean up
        vs_module._async_client = None
