"""Batch operations tasks for maintenance and cleanup."""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.inbound.workers.exceptions import (
    DatabaseConnectionError,
    PermanentError,
    TransientError,
)
from app.adapters.outbound.persistence.postgres.database import get_worker_session_context
from app.adapters.outbound.persistence.postgres.models import PhotoModel
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
    name="batch_operations.cleanup_orphans",
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    retry_backoff_max=300,
)
def cleanup_orphans_task(self, dry_run: bool = True, delete_orphaned_files: bool = False) -> dict:
    """
    Find and optionally clean up orphaned photos and files.

    This task identifies:
    1. Photos in database without corresponding files on disk
    2. Files on disk not tracked in the database

    By default, runs in dry-run mode which only reports findings without making changes.

    Args:
        dry_run: If True, only report findings without making changes (default: True)
        delete_orphaned_files: If True and dry_run=False, delete orphaned files from disk

    Returns:
        Dictionary with cleanup results:
            - orphaned_photos: List of photo IDs without files
            - orphaned_files: List of file paths not in database
            - deleted_photo_records: Count of photo records deleted (if not dry_run)
            - deleted_files: Count of files deleted (if not dry_run and delete_orphaned_files)

    Raises:
        TransientError: For temporary errors that will trigger retry
        PermanentError: For errors that should not be retried
    """
    try:
        return run_async(_cleanup_orphans_async(dry_run, delete_orphaned_files))
    except TransientError:
        logger.warning(
            "Transient error during cleanup, will retry",
            exc_info=True,
            extra={
                "dry_run": dry_run,
                "delete_orphaned_files": delete_orphaned_files,
            },
        )
        raise
    except PermanentError:
        logger.error(
            "Permanent error during cleanup, will not retry",
            exc_info=True,
            extra={
                "dry_run": dry_run,
                "delete_orphaned_files": delete_orphaned_files,
            },
        )
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during cleanup: {e}",
            exc_info=True,
            extra={
                "dry_run": dry_run,
                "delete_orphaned_files": delete_orphaned_files,
            },
        )
        # Treat unexpected errors as transient for safety
        raise TransientError(f"Unexpected cleanup error: {e}") from e


async def _cleanup_orphans_async(
    dry_run: bool, delete_orphaned_files: bool
) -> dict:
    """Async implementation of orphan cleanup."""
    results = {
        "orphaned_photos": [],
        "orphaned_files": [],
        "deleted_photo_records": 0,
        "deleted_files": 0,
        "dry_run": dry_run,
    }

    try:
        async with get_worker_session_context() as session:
            # Step 1: Find photos in DB without files on disk
            logger.info("Scanning database for photos without files on disk...")
            orphaned_photos = await _find_orphaned_photos(session)
            results["orphaned_photos"] = [str(photo_id) for photo_id in orphaned_photos]

            if orphaned_photos:
                logger.warning(
                    f"Found {len(orphaned_photos)} photos in database without files on disk",
                    extra={"count": len(orphaned_photos)},
                )

                if not dry_run:
                    # Delete orphaned photo records from database
                    logger.info(f"Deleting {len(orphaned_photos)} orphaned photo records...")
                    deleted_count = await _delete_orphaned_photos(session, orphaned_photos)
                    await session.commit()
                    results["deleted_photo_records"] = deleted_count
                    logger.info(f"Deleted {deleted_count} orphaned photo records from database")
            else:
                logger.info("No orphaned photos found in database")

            # Step 2: Find files on disk not in database
            logger.info("Scanning storage for files not in database...")
            orphaned_files = await _find_orphaned_files(session)
            results["orphaned_files"] = [str(file_path) for file_path in orphaned_files]

            if orphaned_files:
                logger.warning(
                    f"Found {len(orphaned_files)} files on disk not tracked in database",
                    extra={"count": len(orphaned_files)},
                )

                if not dry_run and delete_orphaned_files:
                    # Delete orphaned files from disk
                    logger.info(f"Deleting {len(orphaned_files)} orphaned files from disk...")
                    deleted_count = await _delete_orphaned_files(orphaned_files)
                    results["deleted_files"] = deleted_count
                    logger.info(f"Deleted {deleted_count} orphaned files from disk")
            else:
                logger.info("No orphaned files found on disk")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Cleanup failed: {e}") from e

    # Log summary
    logger.info(
        "Cleanup completed",
        extra={
            "dry_run": dry_run,
            "orphaned_photos_count": len(results["orphaned_photos"]),
            "orphaned_files_count": len(results["orphaned_files"]),
            "deleted_photo_records": results["deleted_photo_records"],
            "deleted_files": results["deleted_files"],
        },
    )

    return results


async def _find_orphaned_photos(session) -> list[UUID]:
    """Find photos in database without files on disk.

    Args:
        session: Database session

    Returns:
        List of photo IDs that have no corresponding file on disk
    """
    orphaned_ids = []

    # Get all photos with local storage paths
    stmt = select(PhotoModel.id, PhotoModel.storage_path).where(
        PhotoModel.storage_path.isnot(None)
    )
    result = await session.execute(stmt)
    photos = result.all()

    logger.debug(f"Checking {len(photos)} photos with storage paths...")

    for photo_id, storage_path in photos:
        if not storage_path:
            continue

        # Check if file exists
        full_path = settings.storage_photos_path / storage_path
        if not full_path.exists():
            orphaned_ids.append(photo_id)
            logger.debug(f"Photo {photo_id} missing file at {full_path}")

    return orphaned_ids


async def _delete_orphaned_photos(session, photo_ids: list[UUID]) -> int:
    """Delete orphaned photo records from database.

    Args:
        session: Database session
        photo_ids: List of photo IDs to delete

    Returns:
        Number of records deleted
    """
    if not photo_ids:
        return 0

    # Delete photos in batches to avoid huge queries
    batch_size = 100
    total_deleted = 0

    for i in range(0, len(photo_ids), batch_size):
        batch = photo_ids[i : i + batch_size]

        # Get photos to delete
        stmt = select(PhotoModel).where(PhotoModel.id.in_(batch))
        result = await session.execute(stmt)
        photos = result.scalars().all()

        # Delete each photo
        for photo in photos:
            await session.delete(photo)
            total_deleted += 1

        await session.flush()

    return total_deleted


async def _find_orphaned_files(session) -> list[Path]:
    """Find files on disk not tracked in database.

    Args:
        session: Database session

    Returns:
        List of file paths that are not in the database
    """
    orphaned_files = []

    # Get all storage paths from database
    stmt = select(PhotoModel.storage_path).where(PhotoModel.storage_path.isnot(None))
    result = await session.execute(stmt)
    db_paths = {row[0] for row in result.all()}

    logger.debug(f"Found {len(db_paths)} storage paths in database")

    # Scan storage directory
    storage_root = settings.storage_photos_path
    if not storage_root.exists():
        logger.warning(f"Storage directory does not exist: {storage_root}")
        return orphaned_files

    # Walk through storage directory
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif"}
    file_count = 0

    for file_path in storage_root.rglob("*"):
        if not file_path.is_file():
            continue

        # Only check image files
        if file_path.suffix.lower() not in image_extensions:
            continue

        file_count += 1

        # Get relative path from storage root
        try:
            relative_path = str(file_path.relative_to(storage_root))
        except ValueError:
            logger.warning(f"Could not get relative path for {file_path}")
            continue

        # Check if path is in database
        if relative_path not in db_paths:
            orphaned_files.append(file_path)
            logger.debug(f"Orphaned file not in database: {relative_path}")

    logger.debug(f"Scanned {file_count} image files in storage")

    return orphaned_files


async def _delete_orphaned_files(file_paths: list[Path]) -> int:
    """Delete orphaned files from disk.

    Args:
        file_paths: List of file paths to delete

    Returns:
        Number of files deleted
    """
    deleted_count = 0

    for file_path in file_paths:
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_count += 1
                logger.debug(f"Deleted orphaned file: {file_path}")
        except OSError as e:
            logger.error(f"Failed to delete file {file_path}: {e}")

    return deleted_count
