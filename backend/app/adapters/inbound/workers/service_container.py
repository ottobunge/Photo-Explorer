"""Service container for dependency injection in worker tasks.

This container provides lazy-loaded singleton instances of external services
(ML services, vector store, file storage) for use in Celery worker tasks.

The container uses lazy initialization to avoid loading heavy services during
import time, and registers a cleanup handler to ensure resources are properly
released when the worker shuts down.

Example usage:
    from app.adapters.inbound.workers.service_container import get_services

    async def _my_task_async():
        services = get_services()

        # Access services via container
        embedding = await services.ml_services.encode_image(image_data)
        await services.vector_store.store_photo_embedding(photo_id, embedding)
        await services.file_storage.save_photo(data, filename)
"""

import logging
from typing import TYPE_CHECKING, Optional

from celery.signals import worker_shutting_down

if TYPE_CHECKING:
    from app.adapters.outbound.ml.service import MLServices  # type: ignore[import-untyped]
    from app.adapters.outbound.persistence.qdrant.vector_store import QdrantVectorStore
    from app.adapters.outbound.storage.local_file_storage import LocalFileStorage

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Dependency injection container for worker tasks.

    Provides lazy-loaded singleton instances of:
    - ML services (CLIP encoder, face detection)
    - Vector store (Qdrant)
    - File storage (local filesystem)

    Services are initialized on first access and reused across all tasks
    in the worker process.
    """

    def __init__(self) -> None:
        """Initialize container with empty service references."""
        self._ml_services: Optional["MLServices"] = None
        self._vector_store: Optional["QdrantVectorStore"] = None
        self._file_storage: Optional["LocalFileStorage"] = None

    @property
    def ml_services(self) -> "MLServices":
        """Get ML services instance (lazy-loaded singleton).

        Returns:
            MLServices instance for encoding images and detecting faces
        """
        if self._ml_services is None:
            from app.adapters.outbound.ml import get_ml_services

            self._ml_services = get_ml_services()
            logger.debug("Initialized ML services in worker container")
        return self._ml_services

    @property
    def vector_store(self) -> "QdrantVectorStore":
        """Get vector store instance (lazy-loaded singleton).

        Returns:
            QdrantVectorStore instance for storing/searching embeddings
        """
        if self._vector_store is None:
            from app.adapters.outbound.persistence.qdrant import QdrantVectorStore

            self._vector_store = QdrantVectorStore()
            logger.debug("Initialized vector store in worker container")
        return self._vector_store

    @property
    def file_storage(self) -> "LocalFileStorage":
        """Get file storage instance (lazy-loaded singleton).

        Returns:
            LocalFileStorage instance for reading/writing photo files
        """
        if self._file_storage is None:
            from app.adapters.outbound.storage import LocalFileStorage

            self._file_storage = LocalFileStorage()
            logger.debug("Initialized file storage in worker container")
        return self._file_storage

    def close(self) -> None:
        """Cleanup resources.

        Called automatically when worker shuts down via signal handler.
        Attempts to close each service that has a close() method.
        Logs warnings for any errors but continues closing other services.
        """
        services = [
            ("ML services", self._ml_services),
            ("Vector store", self._vector_store),
            ("File storage", self._file_storage),
        ]

        for service_name, service in services:
            if service and hasattr(service, "close"):
                try:
                    service.close()
                    logger.info(f"Closed {service_name}")
                except Exception as e:
                    logger.warning(f"Error closing {service_name}: {e}")


# Global singleton instance
_container: Optional[ServiceContainer] = None


def get_services() -> ServiceContainer:
    """Get the global service container instance.

    Creates the container on first call and returns the same instance
    for all subsequent calls within the worker process.

    Returns:
        ServiceContainer instance with lazy-loaded services
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
        logger.debug("Created global service container")
    return _container


# Register cleanup handler with Celery
@worker_shutting_down.connect  # type: ignore[misc]
def cleanup_services(**kwargs: object) -> None:
    """Cleanup services when worker shuts down.

    This signal handler is automatically called by Celery when the worker
    process is shutting down, ensuring resources are properly released.

    Args:
        **kwargs: Signal arguments (unused but required by Celery)
    """
    global _container
    if _container is not None:
        logger.info("Worker shutting down, cleaning up service container")
        _container.close()
        _container = None
