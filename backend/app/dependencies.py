"""FastAPI dependency injection setup."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.ml import MLServicesAdapter
from app.adapters.outbound.persistence.postgres import (
    AlbumRepositoryPostgres,
    ConnectorRepositoryPostgres,
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
    get_async_session,
)
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.adapters.outbound.storage import LocalFileStorage
from app.application.ports.inbound import FaceUseCases, PhotoUseCases, SearchUseCases
from app.application.ports.outbound import (
    AlbumRepository,
    ConnectorRepository,
    FaceRepository,
    FileStorage,
    MLServices,
    PhotoRepository,
    VectorStore,
)
from app.application.services import FaceService, PhotoService, SearchService


# Database session dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_async_session():
        yield session


# Type alias for injected session
DbSession = Annotated[AsyncSession, Depends(get_db)]


# Singleton instances for services that should be shared
@lru_cache
def get_vector_store() -> VectorStore:
    """Get singleton VectorStore instance."""
    return QdrantVectorStore()


@lru_cache
def get_file_storage() -> FileStorage:
    """Get singleton FileStorage instance."""
    return LocalFileStorage()


@lru_cache
def get_ml_services() -> MLServices:
    """Get singleton MLServices instance."""
    return MLServicesAdapter()


# Repository factories (need session, so not cached)
def get_photo_repository(session: DbSession) -> PhotoRepository:
    """Get PhotoRepository with injected session."""
    return PhotoRepositoryPostgres(session)


def get_album_repository(session: DbSession) -> AlbumRepository:
    """Get AlbumRepository with injected session."""
    return AlbumRepositoryPostgres(session)


def get_face_repository(session: DbSession) -> FaceRepository:
    """Get FaceRepository with injected session."""
    return FaceRepositoryPostgres(session)


def get_connector_repository(session: DbSession) -> ConnectorRepository:
    """Get ConnectorRepository with injected session."""
    return ConnectorRepositoryPostgres(session)


# Type aliases for dependency injection
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
FileStorageDep = Annotated[FileStorage, Depends(get_file_storage)]
MLServicesDep = Annotated[MLServices, Depends(get_ml_services)]

PhotoRepoDep = Annotated[PhotoRepository, Depends(get_photo_repository)]
AlbumRepoDep = Annotated[AlbumRepository, Depends(get_album_repository)]
FaceRepoDep = Annotated[FaceRepository, Depends(get_face_repository)]
ConnectorRepoDep = Annotated[ConnectorRepository, Depends(get_connector_repository)]


# Convenience class for injecting all common dependencies
class ServiceDependencies:
    """Container for all service dependencies."""

    def __init__(
        self,
        session: DbSession,
        vector_store: VectorStoreDep,
        file_storage: FileStorageDep,
        ml_services: MLServicesDep,
    ) -> None:
        self.session = session
        self.vector_store = vector_store
        self.file_storage = file_storage
        self.ml_services = ml_services

        # Create repositories with session
        self.photo_repo = PhotoRepositoryPostgres(session)
        self.album_repo = AlbumRepositoryPostgres(session)
        self.face_repo = FaceRepositoryPostgres(session)
        self.connector_repo = ConnectorRepositoryPostgres(session)


def get_service_dependencies(
    session: DbSession,
    vector_store: VectorStoreDep,
    file_storage: FileStorageDep,
    ml_services: MLServicesDep,
) -> ServiceDependencies:
    """Get all service dependencies in one injection."""
    return ServiceDependencies(
        session=session,
        vector_store=vector_store,
        file_storage=file_storage,
        ml_services=ml_services,
    )


ServicesDep = Annotated[ServiceDependencies, Depends(get_service_dependencies)]


# Application service factories
def get_photo_service(deps: ServicesDep) -> PhotoUseCases:
    """Get PhotoService with injected dependencies."""
    return PhotoService(
        photo_repo=deps.photo_repo,
        file_storage=deps.file_storage,
        vector_store=deps.vector_store,
    )


def get_search_service(deps: ServicesDep) -> SearchUseCases:
    """Get SearchService with injected dependencies."""
    return SearchService(
        photo_repo=deps.photo_repo,
        face_repo=deps.face_repo,
        vector_store=deps.vector_store,
        ml_services=deps.ml_services,
    )


def get_face_service(deps: ServicesDep) -> FaceUseCases:
    """Get FaceService with injected dependencies."""
    return FaceService(
        face_repo=deps.face_repo,
        file_storage=deps.file_storage,
        vector_store=deps.vector_store,
    )


# Type aliases for service injection
PhotoServiceDep = Annotated[PhotoUseCases, Depends(get_photo_service)]
SearchServiceDep = Annotated[SearchUseCases, Depends(get_search_service)]
FaceServiceDep = Annotated[FaceUseCases, Depends(get_face_service)]
