# PostgreSQL Repository implementations
from app.adapters.outbound.persistence.postgres.repositories.album_repository import (
    AlbumRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.repositories.connector_repository import (
    ConnectorRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.repositories.face_repository import (
    FaceRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
    PhotoRepositoryPostgres,
)

__all__ = [
    "PhotoRepositoryPostgres",
    "AlbumRepositoryPostgres",
    "FaceRepositoryPostgres",
    "ConnectorRepositoryPostgres",
]
