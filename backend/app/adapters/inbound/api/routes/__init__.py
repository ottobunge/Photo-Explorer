"""API route modules."""

from app.adapters.inbound.api.routes import (
    albums,
    connectors,
    faces,
    folders,
    models,
    photos,
    search,
    settings,
)

__all__ = ["photos", "albums", "search", "faces", "folders", "connectors", "settings", "models"]
