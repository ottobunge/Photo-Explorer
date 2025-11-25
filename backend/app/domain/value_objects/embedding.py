"""Embedding value object for vector representations."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Embedding:
    """
    Immutable embedding vector.

    Represents a dense vector embedding from CLIP or face recognition models.
    """

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        """Validate embedding."""
        if len(self.values) == 0:
            raise ValueError("Embedding cannot be empty")

    @classmethod
    def from_list(cls, values: Sequence[float]) -> "Embedding":
        """Create an embedding from a list of floats."""
        return cls(values=tuple(values))

    @property
    def dimension(self) -> int:
        """Get the dimensionality of the embedding."""
        return len(self.values)

    def to_list(self) -> list[float]:
        """Convert to a list of floats."""
        return list(self.values)

    def __len__(self) -> int:
        """Return the dimension of the embedding."""
        return self.dimension
