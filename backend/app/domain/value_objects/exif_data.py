"""EXIF metadata value objects."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class GpsCoordinates:
    """Immutable GPS coordinates."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Validate coordinates."""
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")

    def to_tuple(self) -> tuple[float, float]:
        """Convert to (lat, lng) tuple."""
        return (self.latitude, self.longitude)


@dataclass(frozen=True)
class ExifData:
    """
    Immutable EXIF metadata extracted from a photo.

    Contains camera settings, date/time, and location information.
    """

    # Camera info
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None

    # Capture settings
    iso: Optional[int] = None
    aperture: Optional[str] = None
    shutter_speed: Optional[str] = None
    focal_length: Optional[str] = None
    flash: Optional[bool] = None

    # Date/time
    date_taken: Optional[datetime] = None

    # Location
    gps: Optional[GpsCoordinates] = None

    # Image info
    orientation: Optional[int] = None
    software: Optional[str] = None

    @property
    def has_location(self) -> bool:
        """Check if GPS coordinates are available."""
        return self.gps is not None

    @property
    def camera_name(self) -> Optional[str]:
        """Get a formatted camera name."""
        if self.camera_make and self.camera_model:
            # Avoid duplicating make in model
            if self.camera_model.startswith(self.camera_make):
                return self.camera_model
            return f"{self.camera_make} {self.camera_model}"
        return self.camera_model or self.camera_make

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result: dict = {}
        if self.camera_make:
            result["camera_make"] = self.camera_make
        if self.camera_model:
            result["camera_model"] = self.camera_model
        if self.lens_model:
            result["lens_model"] = self.lens_model
        if self.iso:
            result["iso"] = self.iso
        if self.aperture:
            result["aperture"] = self.aperture
        if self.shutter_speed:
            result["shutter_speed"] = self.shutter_speed
        if self.focal_length:
            result["focal_length"] = self.focal_length
        if self.flash is not None:
            result["flash"] = self.flash
        if self.date_taken:
            result["date_taken"] = self.date_taken.isoformat()
        if self.gps:
            result["gps"] = {"lat": self.gps.latitude, "lng": self.gps.longitude}
        if self.orientation:
            result["orientation"] = self.orientation
        if self.software:
            result["software"] = self.software
        return result
