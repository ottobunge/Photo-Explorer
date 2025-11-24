"""Service for initializing default connectors.

Ensures required system connectors (like the default Uploads connector) exist.
"""

import logging
from pathlib import Path

from app.application.ports.outbound.connector_repository import ConnectorRepository
from app.domain.entities.connector import Connector, ConnectorType

logger = logging.getLogger(__name__)


async def ensure_default_upload_connector(
    connector_repo: ConnectorRepository,
    uploads_path: Path,
) -> Connector:
    """Ensure the default upload connector exists.

    Creates a default "Uploads" connector if it doesn't already exist.
    This connector is used for ad-hoc photo uploads via the API.

    Args:
        connector_repo: Repository for connector persistence
        uploads_path: Path where uploaded photos should be stored

    Returns:
        The default upload connector (existing or newly created)
    """
    # Check if an upload connector already exists
    connectors = await connector_repo.find_all()
    upload_connectors = [c for c in connectors if c.type == ConnectorType.UPLOAD]

    if upload_connectors:
        logger.info(f"Default upload connector already exists: {upload_connectors[0].id}")
        return upload_connectors[0]

    # Create the default upload connector
    logger.info(f"Creating default upload connector at {uploads_path}")
    upload_connector = Connector.create_upload(upload_path=str(uploads_path))

    # Persist the connector
    saved_connector = await connector_repo.save(upload_connector)
    logger.info(f"Default upload connector created: {saved_connector.id}")

    return saved_connector
