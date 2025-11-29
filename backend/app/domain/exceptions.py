"""Domain-specific exceptions."""


class DomainException(Exception):
    """Base exception for domain errors.

    All domain exceptions inherit from this class to allow
    consistent handling across the application.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ValidationException(DomainException):
    """Raised when domain validation fails."""


class EntityNotFoundException(DomainException):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id '{entity_id}' not found")


class InvalidOperationException(DomainException):
    """Raised when an operation is not valid in the current state."""


# Connector-specific exceptions
class ConnectorNotFoundError(EntityNotFoundException):
    """Raised when a connector is not found."""

    def __init__(self, connector_id: str) -> None:
        super().__init__("Connector", connector_id)


class ConnectorAlreadyExistsError(DomainException):
    """Raised when attempting to create a duplicate connector."""

    def __init__(self, connector_name: str) -> None:
        super().__init__(f"Connector with name '{connector_name}' already exists")


class TokenExpiredError(DomainException):
    """Raised when an authentication token has expired."""

    def __init__(self, connector_id: str) -> None:
        self.connector_id = connector_id
        super().__init__(f"Authentication token for connector '{connector_id}' has expired")


class TokenNotFoundError(DomainException):
    """Raised when authentication tokens are not found."""

    def __init__(self, connector_id: str) -> None:
        self.connector_id = connector_id
        super().__init__(f"No authentication tokens found for connector '{connector_id}'")


class SyncInProgressError(InvalidOperationException):
    """Raised when attempting to sync while a sync is already in progress."""

    def __init__(self, connector_id: str) -> None:
        self.connector_id = connector_id
        super().__init__(f"Sync is already in progress for connector '{connector_id}'")


# Photo-specific exceptions
class PhotoNotFoundError(EntityNotFoundException):
    """Raised when a photo is not found."""

    def __init__(self, photo_id: str) -> None:
        super().__init__("Photo", photo_id)


class PhotoAlreadyExistsError(DomainException):
    """Raised when attempting to import a duplicate photo."""

    def __init__(self, file_path: str) -> None:
        super().__init__(f"Photo at path '{file_path}' already exists")


# Album-specific exceptions
class AlbumNotFoundError(EntityNotFoundException):
    """Raised when an album is not found."""

    def __init__(self, album_id: str) -> None:
        super().__init__("Album", album_id)


# Face-specific exceptions
class FaceNotFoundError(EntityNotFoundException):
    """Raised when a face is not found."""

    def __init__(self, face_id: str) -> None:
        super().__init__("Face", face_id)


class FaceClusterNotFoundError(EntityNotFoundException):
    """Raised when a face cluster is not found."""

    def __init__(self, cluster_id: str) -> None:
        super().__init__("FaceCluster", cluster_id)


class ClusteringInProgressError(InvalidOperationException):
    """Raised when attempting to cluster faces while clustering is already in progress."""

    def __init__(self) -> None:
        super().__init__("Face clustering is already in progress")


# Storage exceptions
class StorageError(DomainException):
    """Raised when a storage operation fails."""


class PathSecurityError(StorageError):
    """Raised when a path traversal or security violation is detected."""

    def __init__(self, message: str, attempted_path: str | None = None) -> None:
        self.attempted_path = attempted_path
        super().__init__(message)


class FileNotFoundError(StorageError):
    """Raised when a file is not found in storage."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        super().__init__(f"File not found: {file_path}")


class InsufficientStorageError(StorageError):
    """Raised when there is insufficient storage space."""

    def __init__(self, required_bytes: int, available_bytes: int) -> None:
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes
        super().__init__(
            f"Insufficient storage: required {required_bytes} bytes, "
            f"only {available_bytes} bytes available"
        )


# ML Model exceptions
class ModelNotLoadedError(DomainException):
    """Raised when attempting to use an ML model that hasn't been loaded."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        super().__init__(f"ML model '{model_name}' is not loaded")


class ModelInferenceError(DomainException):
    """Raised when ML model inference fails."""

    def __init__(self, model_name: str, reason: str) -> None:
        self.model_name = model_name
        self.reason = reason
        super().__init__(f"Inference failed for model '{model_name}': {reason}")

