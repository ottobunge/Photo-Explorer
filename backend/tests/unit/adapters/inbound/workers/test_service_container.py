"""Unit tests for ServiceContainer."""

from unittest.mock import Mock, patch

import pytest

from app.adapters.inbound.workers.service_container import (
    ServiceContainer,
    cleanup_services,
    get_services,
)


class TestServiceContainer:
    """Unit tests for service container."""

    def test_lazy_initialization_ml_services(self) -> None:
        """When ML services not accessed, should not be loaded."""
        # Arrange
        container = ServiceContainer()

        # Assert
        assert container._ml_services is None

    def test_lazy_initialization_vector_store(self) -> None:
        """When vector store not accessed, should not be loaded."""
        # Arrange
        container = ServiceContainer()

        # Assert
        assert container._vector_store is None

    def test_lazy_initialization_file_storage(self) -> None:
        """When file storage not accessed, should not be loaded."""
        # Arrange
        container = ServiceContainer()

        # Assert
        assert container._file_storage is None

    @patch("app.adapters.outbound.ml.get_ml_services")
    def test_ml_services_loads_on_access(self, mock_get_ml: Mock) -> None:
        """When ML services accessed, should load and cache."""
        # Arrange
        container = ServiceContainer()
        mock_ml = Mock()
        mock_get_ml.return_value = mock_ml

        # Act
        ml = container.ml_services

        # Assert
        assert ml is mock_ml
        assert container._ml_services is mock_ml
        mock_get_ml.assert_called_once()

    @patch("app.adapters.outbound.persistence.qdrant.QdrantVectorStore")
    def test_vector_store_loads_on_access(self, mock_qdrant_class: Mock) -> None:
        """When vector store accessed, should load and cache."""
        # Arrange
        container = ServiceContainer()
        mock_store = Mock()
        mock_qdrant_class.return_value = mock_store

        # Act
        store = container.vector_store

        # Assert
        assert store is mock_store
        assert container._vector_store is mock_store
        mock_qdrant_class.assert_called_once()

    @patch("app.adapters.outbound.storage.LocalFileStorage")
    def test_file_storage_loads_on_access(self, mock_storage_class: Mock) -> None:
        """When file storage accessed, should load and cache."""
        # Arrange
        container = ServiceContainer()
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Act
        storage = container.file_storage

        # Assert
        assert storage is mock_storage
        assert container._file_storage is mock_storage
        mock_storage_class.assert_called_once()

    @patch("app.adapters.outbound.ml.get_ml_services")
    def test_singleton_behavior_ml_services(self, mock_get_ml: Mock) -> None:
        """When accessing ML services multiple times, should return same instance."""
        # Arrange
        container = ServiceContainer()
        mock_ml = Mock()
        mock_get_ml.return_value = mock_ml

        # Act
        ml1 = container.ml_services
        ml2 = container.ml_services

        # Assert
        assert ml1 is ml2
        assert mock_get_ml.call_count == 1  # Only called once

    @patch("app.adapters.outbound.persistence.qdrant.QdrantVectorStore")
    def test_singleton_behavior_vector_store(self, mock_qdrant_class: Mock) -> None:
        """When accessing vector store multiple times, should return same instance."""
        # Arrange
        container = ServiceContainer()
        mock_store = Mock()
        mock_qdrant_class.return_value = mock_store

        # Act
        store1 = container.vector_store
        store2 = container.vector_store

        # Assert
        assert store1 is store2
        assert mock_qdrant_class.call_count == 1

    @patch("app.adapters.outbound.storage.LocalFileStorage")
    def test_singleton_behavior_file_storage(self, mock_storage_class: Mock) -> None:
        """When accessing file storage multiple times, should return same instance."""
        # Arrange
        container = ServiceContainer()
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Act
        storage1 = container.file_storage
        storage2 = container.file_storage

        # Assert
        assert storage1 is storage2
        assert mock_storage_class.call_count == 1

    @patch("app.adapters.outbound.ml.get_ml_services")
    @patch("app.adapters.outbound.persistence.qdrant.QdrantVectorStore")
    @patch("app.adapters.outbound.storage.LocalFileStorage")
    def test_close_calls_service_close_methods(
        self,
        mock_storage_class: Mock,
        mock_qdrant_class: Mock,
        mock_get_ml: Mock,
    ) -> None:
        """When closing container, should call close() on all loaded services."""
        # Arrange
        container = ServiceContainer()

        # Create mock services with close methods
        mock_ml = Mock()
        mock_ml.close = Mock()
        mock_get_ml.return_value = mock_ml

        mock_store = Mock()
        mock_store.close = Mock()
        mock_qdrant_class.return_value = mock_store

        mock_storage = Mock()
        mock_storage.close = Mock()
        mock_storage_class.return_value = mock_storage

        # Access all services to load them
        _ = container.ml_services
        _ = container.vector_store
        _ = container.file_storage

        # Act
        container.close()

        # Assert
        mock_ml.close.assert_called_once()
        mock_store.close.assert_called_once()
        mock_storage.close.assert_called_once()

    @patch("app.adapters.outbound.ml.get_ml_services")
    def test_close_handles_missing_close_method(self, mock_get_ml: Mock) -> None:
        """When service has no close method, should not error."""
        # Arrange
        container = ServiceContainer()

        # Create mock service without close method
        mock_ml = Mock(spec=[])  # No methods
        mock_get_ml.return_value = mock_ml

        _ = container.ml_services

        # Act - should not raise
        container.close()

    @patch("app.adapters.outbound.ml.get_ml_services")
    def test_close_handles_close_errors(self, mock_get_ml: Mock, caplog: pytest.LogCaptureFixture) -> None:
        """When close() raises exception, should log warning and continue."""
        # Arrange
        container = ServiceContainer()

        # Create mock service with failing close
        mock_ml = Mock()
        mock_ml.close = Mock(side_effect=Exception("Close failed"))
        mock_get_ml.return_value = mock_ml

        _ = container.ml_services

        # Act
        import logging
        with caplog.at_level(logging.WARNING):
            container.close()

        # Assert
        assert "Error closing ML services" in caplog.text

    def test_close_with_no_loaded_services(self) -> None:
        """When closing container with no loaded services, should not error."""
        # Arrange
        container = ServiceContainer()

        # Act - should not raise
        container.close()


class TestGetServicesFunction:
    """Tests for get_services() global function."""

    def test_get_services_creates_container(self) -> None:
        """When called first time, should create new container."""
        # Reset global state
        import app.adapters.inbound.workers.service_container as sc_module
        sc_module._container = None

        # Act
        container = get_services()

        # Assert
        assert container is not None
        assert isinstance(container, ServiceContainer)

    def test_get_services_returns_singleton(self) -> None:
        """When called multiple times, should return same container."""
        # Reset global state
        import app.adapters.inbound.workers.service_container as sc_module
        sc_module._container = None

        # Act
        container1 = get_services()
        container2 = get_services()

        # Assert
        assert container1 is container2


class TestCleanupServicesSignalHandler:
    """Tests for cleanup_services signal handler."""

    def test_cleanup_services_closes_container(self) -> None:
        """When worker shuts down, should close container."""
        # Arrange
        import app.adapters.inbound.workers.service_container as sc_module

        # Create a mock container
        mock_container = Mock(spec=ServiceContainer)
        mock_container.close = Mock()
        sc_module._container = mock_container

        # Act
        cleanup_services()

        # Assert
        mock_container.close.assert_called_once()

    def test_cleanup_services_resets_global_container(self) -> None:
        """When cleanup called, should reset global container to None."""
        # Arrange
        import app.adapters.inbound.workers.service_container as sc_module

        # Create a mock container
        mock_container = Mock(spec=ServiceContainer)
        sc_module._container = mock_container

        # Act
        cleanup_services()

        # Assert
        assert sc_module._container is None

    def test_cleanup_services_handles_none_container(self) -> None:
        """When container is None, cleanup should not error."""
        # Arrange
        import app.adapters.inbound.workers.service_container as sc_module
        sc_module._container = None

        # Act - should not raise
        cleanup_services()


class TestServiceContainerIntegration:
    """Integration-style tests for service container behavior."""

    @patch("app.adapters.outbound.ml.get_ml_services")
    @patch("app.adapters.outbound.persistence.qdrant.QdrantVectorStore")
    @patch("app.adapters.outbound.storage.LocalFileStorage")
    def test_full_lifecycle(
        self,
        mock_storage_class: Mock,
        mock_qdrant_class: Mock,
        mock_get_ml: Mock,
    ) -> None:
        """Test complete lifecycle: create, use, close."""
        # Arrange
        mock_ml = Mock()
        mock_ml.close = Mock()
        mock_get_ml.return_value = mock_ml

        mock_store = Mock()
        mock_store.close = Mock()
        mock_qdrant_class.return_value = mock_store

        mock_storage = Mock()
        mock_storage.close = Mock()
        mock_storage_class.return_value = mock_storage

        # Act
        container = ServiceContainer()

        # Use all services
        ml = container.ml_services
        store = container.vector_store
        storage = container.file_storage

        # Verify services are loaded
        assert ml is mock_ml
        assert store is mock_store
        assert storage is mock_storage

        # Close container
        container.close()

        # Assert all services were closed
        mock_ml.close.assert_called_once()
        mock_store.close.assert_called_once()
        mock_storage.close.assert_called_once()

    @patch("app.adapters.outbound.ml.get_ml_services")
    def test_partial_service_usage(self, mock_get_ml: Mock) -> None:
        """When only some services used, only those should be in memory."""
        # Arrange
        container = ServiceContainer()
        mock_ml = Mock()
        mock_get_ml.return_value = mock_ml

        # Act - only access ML services
        _ = container.ml_services

        # Assert
        assert container._ml_services is not None
        assert container._vector_store is None
        assert container._file_storage is None
