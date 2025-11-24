# PostgreSQL persistence adapters
from app.adapters.outbound.persistence.postgres.database import (
    close_db,
    get_async_session,
    get_engine,
    get_session_context,
    init_db,
)
from app.adapters.outbound.persistence.postgres.mappers import (
    AlbumMapper,
    ConnectorMapper,
    FaceClusterMapper,
    FaceMapper,
    PhotoMapper,
)
from app.adapters.outbound.persistence.postgres.models import (
    AlbumModel,
    Base,
    ConnectorModel,
    FaceClusterModel,
    FaceModel,
    PhotoModel,
)
from app.adapters.outbound.persistence.postgres.repositories import (
    AlbumRepositoryPostgres,
    ConnectorRepositoryPostgres,
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)

__all__ = [
    # Database
    "get_engine",
    "get_async_session",
    "get_session_context",
    "init_db",
    "close_db",
    # Models
    "Base",
    "PhotoModel",
    "AlbumModel",
    "FaceModel",
    "FaceClusterModel",
    "ConnectorModel",
    # Mappers
    "PhotoMapper",
    "AlbumMapper",
    "FaceMapper",
    "FaceClusterMapper",
    "ConnectorMapper",
    # Repositories
    "PhotoRepositoryPostgres",
    "AlbumRepositoryPostgres",
    "FaceRepositoryPostgres",
    "ConnectorRepositoryPostgres",
]
