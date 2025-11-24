"""Strongly-typed ID value objects."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class _TypedId:
    """Base class for strongly-typed IDs wrapping UUID."""

    value: UUID

    def __post_init__(self) -> None:
        # Convert non-standard UUID types (like asyncpg's UUID) to Python UUID
        if not isinstance(self.value, UUID):
            # Use object.__setattr__ because dataclass is frozen
            object.__setattr__(self, "value", UUID(str(self.value)))

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class PhotoId(_TypedId):
    """Strongly-typed ID for Photo entities."""

    pass


@dataclass(frozen=True)
class AlbumId(_TypedId):
    """Strongly-typed ID for Album entities."""

    pass


@dataclass(frozen=True)
class FaceId(_TypedId):
    """Strongly-typed ID for Face entities."""

    pass


@dataclass(frozen=True)
class FaceClusterId(_TypedId):
    """Strongly-typed ID for FaceCluster entities."""

    pass


@dataclass(frozen=True)
class ConnectorId(_TypedId):
    """Strongly-typed ID for Connector entities."""

    pass
