"""Type definitions for application services."""

from typing import TYPE_CHECKING, NotRequired, TypedDict
from uuid import UUID

if TYPE_CHECKING:
    from app.domain.value_objects.scene_classification import SceneClassification


class ProcessingResultDict(TypedDict):
    """Result from photo processing."""

    status: str
    photo_id: str
    thumbnail_path: NotRequired[str]


class FaceDetectionResultDict(TypedDict):
    """Result from face detection."""

    status: str
    photo_id: str
    faces_detected: int
    faces_saved: int
    faces_in_vector_store: NotRequired[int]
    face_ids: NotRequired[list[str]]


class LocalConnectorConfigDict(TypedDict, total=False):
    """Configuration for local folder connector."""

    path: str
    watch_for_changes: bool
    sync_interval_minutes: int
    recursive: bool
    ignore_patterns: list[str]
    auto_album: bool
    watch: bool
    email: str  # Can be in any config dict


class GooglePhotosConfigDict(TypedDict, total=False):
    """Configuration for Google Photos connector."""

    email: str
    sync_favorites_only: bool
    sync_interval_hours: int
    max_photo_size: int


class TaskMetadataDict(TypedDict, total=False):
    """Metadata stored for task tracking."""

    task_name: str
    task_id: str
    task_args: list[str]
    task_kwargs: dict[str, object]
    photo_id: str
    connector_id: str
    face_ids: list[str]
    exception: str
    exception_type: str
    traceback: str
    retries: int


class VectorStorePhotoPayload(TypedDict, total=False):
    """Metadata payload for photo vector store."""

    photo_id: str
    filename: str
    connector_type: str


class VectorStoreFacePayload(TypedDict, total=False):
    """Metadata payload for face vector store."""

    photo_id: str
    cluster_id: str | None


class DeliveryInfoDict(TypedDict, total=False):
    """Celery task delivery info."""

    routing_key: str
    exchange: str
    priority: int


class ImageAnalysisDict(TypedDict, total=False):
    """Image analysis results."""

    description: str | None
    scene_classification: "SceneClassification | None"
    detected_objects: list[str]
