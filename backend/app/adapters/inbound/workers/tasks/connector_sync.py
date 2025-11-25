"""Connector sync tasks for background execution."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.inbound.workers.exceptions import TransientError
from app.adapters.inbound.workers.tasks.photo_processing import (
    detect_faces_task,
    process_photo_task,
)
from app.adapters.outbound.connectors.local_folder import LocalFolderScanner
from app.adapters.outbound.persistence.postgres import (
    ConnectorRepositoryPostgres,
    PhotoRepositoryPostgres,
    AlbumRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.database import get_worker_session_context
from app.domain.entities import Album, Connector, Photo
from app.domain.entities.connector import ConnectorStatus, ConnectorType, SyncStats
from app.domain.value_objects import PhotoId

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context.

    Creates a new event loop for each call without setting it as the global
    event loop to avoid race conditions in multi-threaded Celery workers.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="connector_sync.sync_local_folder",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def sync_local_folder_task(self, connector_id: str) -> dict:
    """
    Sync a local folder connector.

    Scans the folder for new, modified, and deleted files.

    Args:
        connector_id: UUID of the connector

    Returns:
        Dictionary with sync results
    """
    return run_async(_sync_local_folder_async(connector_id))


async def _sync_local_folder_async(connector_id: str) -> dict:
    """Async implementation of local folder sync."""
    connector_uuid = UUID(connector_id)
    started_at = datetime.utcnow()

    async with get_worker_session_context() as session:
        connector_repo = ConnectorRepositoryPostgres(session)
        photo_repo = PhotoRepositoryPostgres(session)
        album_repo = AlbumRepositoryPostgres(session)

        # Get connector
        connector = await connector_repo.find_by_id(connector_uuid)
        if not connector:
            return {"status": "error", "message": "Connector not found"}

        if connector.type != ConnectorType.LOCAL:
            return {"status": "error", "message": "Not a local connector"}

        # Mark as syncing
        connector.set_syncing()
        await connector_repo.save(connector)

        try:
            scanner = LocalFolderScanner(connector)

            # Get existing photos for this connector
            existing_photos = await photo_repo.find_by_connector(connector_uuid, limit=100000)
            known_files = {p.source_path: p.id.value for p in existing_photos if p.source_path}

            # Track stats with mutable variables
            total_items = 0
            indexed = 0
            skipped = 0
            failed = 0
            albums_cache: dict[str, UUID] = {}  # subfolder -> album_id

            # Scan for files
            async for metadata in scanner.scan():
                total_items += 1
                source_path = metadata["source_path"]

                # Check if photo already exists
                if source_path in known_files:
                    # Photo exists - check if it needs processing
                    photo_id = known_files[source_path]
                    existing_photo = await photo_repo.find_by_id(photo_id)

                    if existing_photo and existing_photo.processing_status == "pending":
                        # Queue processing for pending photos
                        process_photo_task.delay(str(photo_id))
                        detect_faces_task.delay(str(photo_id))
                        logger.debug(f"Re-queued pending photo for processing: {source_path}")
                        indexed += 1  # Count as indexed since we're triggering processing
                    else:
                        # Photo already processed or processing, skip
                        skipped += 1
                    continue

                try:
                    # Create new photo
                    photo = Photo.create_from_connector(
                        filename=metadata["filename"],
                        connector_type="local",
                        connector_id=connector_uuid,
                        external_id=source_path,  # Use path as external ID
                        source_path=source_path,
                    )

                    # Set metadata
                    photo.set_metadata(
                        mime_type=metadata.get("mime_type"),
                        file_size=metadata.get("file_size"),
                        width=metadata.get("width"),
                        height=metadata.get("height"),
                        taken_at=metadata.get("taken_at"),
                    )

                    # Handle auto-album
                    if connector.config.get("auto_album") and metadata.get("subfolder"):
                        album_id = await _get_or_create_album(
                            album_repo, albums_cache, metadata["subfolder"]
                        )
                        if album_id:
                            photo.add_to_album(album_id)

                    # Save photo
                    photo = await photo_repo.save(photo)
                    indexed += 1

                    logger.debug(f"Indexed photo: {source_path}")

                    # Queue processing task
                    process_photo_task.delay(str(photo.id.value))
                    detect_faces_task.delay(str(photo.id.value))

                except Exception as e:
                    logger.error(f"Error indexing {source_path}: {e}")
                    failed += 1

            # Check for deleted files
            current_paths = set()
            async for metadata in scanner.scan():
                current_paths.add(metadata["source_path"])

            for source_path, photo_id in known_files.items():
                if source_path not in current_paths:
                    # File was deleted
                    photo = await photo_repo.find_by_id(photo_id)
                    if photo:
                        photo.mark_source_deleted()
                        await photo_repo.save(photo)
                        logger.debug(f"Marked as deleted: {source_path}")

            # Create immutable SyncStats value object with final counts
            stats = SyncStats(
                total_items=total_items,
                indexed=indexed,
                skipped=skipped,
                failed=failed,
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

            # Update connector with sync stats
            connector.record_sync(stats)
            await connector_repo.save(connector)

            logger.info(
                f"Sync complete for {connector.name}: "
                f"{indexed} new, {skipped} skipped, {failed} failed"
            )

            return {
                "status": "completed",
                "connector_id": connector_id,
                "total_items": total_items,
                "indexed": indexed,
                "skipped": skipped,
                "failed": failed,
                "duration_seconds": stats.duration_seconds,
            }

        except Exception as e:
            logger.exception(f"Error syncing connector {connector_id}: {e}")
            connector.set_error(str(e))
            await connector_repo.save(connector)
            return {"status": "error", "message": str(e)}


async def _get_or_create_album(
    album_repo: AlbumRepositoryPostgres,
    cache: dict[str, UUID],
    subfolder: str,
) -> UUID | None:
    """Get or create an album for a subfolder."""
    if subfolder in cache:
        return cache[subfolder]

    # Check if album exists
    album = await album_repo.find_by_name(subfolder)
    if album:
        cache[subfolder] = album.id.value
        return album.id.value

    # Create new album
    album = Album.create(name=subfolder)
    album = await album_repo.save(album)
    cache[subfolder] = album.id.value
    return album.id.value


@celery_app.task(
    bind=True,
    name="connector_sync.index_single_file",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def index_single_file_task(self, connector_id: str, file_path: str) -> dict:
    """
    Index a single file (triggered by filesystem watcher).

    Args:
        connector_id: UUID of the connector
        file_path: Path to the file

    Returns:
        Dictionary with indexing result
    """
    return run_async(_index_single_file_async(connector_id, file_path))


async def _index_single_file_async(connector_id: str, file_path: str) -> dict:
    """Async implementation of single file indexing."""
    connector_uuid = UUID(connector_id)

    async with get_worker_session_context() as session:
        connector_repo = ConnectorRepositoryPostgres(session)
        photo_repo = PhotoRepositoryPostgres(session)

        # Get connector
        connector = await connector_repo.find_by_id(connector_uuid)
        if not connector:
            return {"status": "error", "message": "Connector not found"}

        # Check if photo already exists
        existing = await photo_repo.find_by_original_path(file_path)
        if existing:
            return {"status": "skipped", "message": "Photo already indexed"}

        try:
            scanner = LocalFolderScanner(connector)
            from pathlib import Path

            metadata = await scanner._extract_file_metadata(Path(file_path))

            # Create photo
            photo = Photo.create_from_connector(
                filename=metadata["filename"],
                connector_type="local",
                connector_id=connector_uuid,
                external_id=file_path,
                source_path=file_path,
            )

            photo.set_metadata(
                mime_type=metadata.get("mime_type"),
                file_size=metadata.get("file_size"),
                width=metadata.get("width"),
                height=metadata.get("height"),
                taken_at=metadata.get("taken_at"),
            )

            photo = await photo_repo.save(photo)

            # Queue processing
            process_photo_task.delay(str(photo.id.value))
            detect_faces_task.delay(str(photo.id.value))

            return {
                "status": "completed",
                "photo_id": str(photo.id.value),
            }

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="connector_sync.handle_file_deleted",
    autoretry_for=(TransientError, OperationalError, ConnectionError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},  # Fewer retries for deletion events
)
def handle_file_deleted_task(self, connector_id: str, file_path: str) -> dict:
    """
    Handle a deleted file (triggered by filesystem watcher).

    Args:
        connector_id: UUID of the connector
        file_path: Path to the deleted file

    Returns:
        Dictionary with result
    """
    return run_async(_handle_file_deleted_async(connector_id, file_path))


async def _handle_file_deleted_async(connector_id: str, file_path: str) -> dict:
    """Async implementation of file deletion handling."""
    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        # Find photo by source path
        photo = await photo_repo.find_by_original_path(file_path)
        if not photo:
            return {"status": "skipped", "message": "Photo not found"}

        # Mark as source deleted
        photo.mark_source_deleted()
        await photo_repo.save(photo)

        return {
            "status": "completed",
            "photo_id": str(photo.id.value),
        }


@celery_app.task(
    bind=True,
    name="connector_sync.handle_file_moved",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},  # Fewer retries for move events
)
def handle_file_moved_task(self, connector_id: str, old_path: str, new_path: str) -> dict:
    """
    Handle a moved/renamed file (triggered by filesystem watcher).

    Args:
        connector_id: UUID of the connector
        old_path: Original path
        new_path: New path

    Returns:
        Dictionary with result
    """
    return run_async(_handle_file_moved_async(connector_id, old_path, new_path))


async def _handle_file_moved_async(connector_id: str, old_path: str, new_path: str) -> dict:
    """Async implementation of file move handling."""
    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        # Find photo by old source path
        photo = await photo_repo.find_by_original_path(old_path)
        if not photo:
            # Photo wasn't indexed - index it at new location
            return await _index_single_file_async(connector_id, new_path)

        # Update source path
        photo.source_path = new_path
        photo.external_id = new_path
        photo.update_sync()
        await photo_repo.save(photo)

        return {
            "status": "completed",
            "photo_id": str(photo.id.value),
            "old_path": old_path,
            "new_path": new_path,
        }
