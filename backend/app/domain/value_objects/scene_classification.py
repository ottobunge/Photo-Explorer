"""Scene classification value object."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SceneClassification:
    """
    Immutable scene classification result.

    Contains AI-determined scene type and indoor/outdoor classification.
    """

    scene_type: str
    is_indoor: bool
    confidence: Optional[float] = None

    # Common scene types
    SCENE_BEACH = "beach"
    SCENE_MOUNTAIN = "mountain"
    SCENE_CITY = "city"
    SCENE_FOREST = "forest"
    SCENE_HOME = "home"
    SCENE_OFFICE = "office"
    SCENE_RESTAURANT = "restaurant"
    SCENE_PARK = "park"
    SCENE_EVENT = "event"
    SCENE_PORTRAIT = "portrait"
    SCENE_UNKNOWN = "unknown"

    def __post_init__(self) -> None:
        """Validate classification."""
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

    @classmethod
    def indoor(cls, scene_type: str, confidence: Optional[float] = None) -> "SceneClassification":
        """Create an indoor scene classification."""
        return cls(scene_type=scene_type, is_indoor=True, confidence=confidence)

    @classmethod
    def outdoor(cls, scene_type: str, confidence: Optional[float] = None) -> "SceneClassification":
        """Create an outdoor scene classification."""
        return cls(scene_type=scene_type, is_indoor=False, confidence=confidence)

    @classmethod
    def unknown(cls) -> "SceneClassification":
        """Create an unknown scene classification."""
        return cls(scene_type=cls.SCENE_UNKNOWN, is_indoor=False, confidence=None)
