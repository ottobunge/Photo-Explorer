"""Domain-specific exceptions."""


class DomainException(Exception):
    """Base exception for domain errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ValidationException(DomainException):
    """Raised when domain validation fails."""

    pass


class EntityNotFoundException(DomainException):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id '{entity_id}' not found")


class InvalidOperationException(DomainException):
    """Raised when an operation is not valid in the current state."""

    pass
