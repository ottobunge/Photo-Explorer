"""Domain entities - Aggregate roots and entities."""

from app.domain.entities.album import Album
from app.domain.entities.connector import (
    Connector,
    ConnectorStatus,
    ConnectorType,
)
from app.domain.value_objects import SyncStats
from app.domain.entities.face import Face
from app.domain.entities.face_cluster import FaceCluster
from app.domain.entities.photo import Photo
from app.domain.entities.task_execution import TaskExecution, TaskExecutionStatus

__all__ = [
    "Photo",
    "Album",
    "Face",
    "FaceCluster",
    "Connector",
    "ConnectorType",
    "ConnectorStatus",
    "SyncStats",
    "TaskExecution",
    "TaskExecutionStatus",
]
