"""BoundingBox value object for face detection regions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """
    Immutable bounding box representing a rectangular region.

    Used primarily for face detection regions within photos.
    """

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        """Validate bounding box dimensions."""
        if self.width <= 0:
            raise ValueError("Width must be positive")
        if self.height <= 0:
            raise ValueError("Height must be positive")
        if self.x < 0:
            raise ValueError("X coordinate cannot be negative")
        if self.y < 0:
            raise ValueError("Y coordinate cannot be negative")

    @property
    def x2(self) -> int:
        """Get the right edge x coordinate."""
        return self.x + self.width

    @property
    def y2(self) -> int:
        """Get the bottom edge y coordinate."""
        return self.y + self.height

    @property
    def center(self) -> tuple[int, int]:
        """Get the center point of the bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        """Get the area of the bounding box."""
        return self.width * self.height

    def to_tuple(self) -> tuple[int, int, int, int]:
        """Convert to (x, y, width, height) tuple."""
        return (self.x, self.y, self.width, self.height)

    def to_xyxy(self) -> tuple[int, int, int, int]:
        """Convert to (x1, y1, x2, y2) format."""
        return (self.x, self.y, self.x2, self.y2)

    @classmethod
    def from_xyxy(cls, x1: int, y1: int, x2: int, y2: int) -> "BoundingBox":
        """Create from (x1, y1, x2, y2) coordinates."""
        return cls(x=x1, y=y1, width=x2 - x1, height=y2 - y1)

    def expand(self, margin: int) -> "BoundingBox":
        """Create a new bounding box expanded by margin pixels."""
        return BoundingBox(
            x=max(0, self.x - margin),
            y=max(0, self.y - margin),
            width=self.width + 2 * margin,
            height=self.height + 2 * margin,
        )
