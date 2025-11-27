"""Photo processing tasks for background execution."""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import DBAPIError, OperationalError

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.inbound.workers.exceptions import (
    DatabaseConnectionError,
    InvalidDataError,
    PermanentError,
    ProcessingError,
    ResourceNotFoundError,
    StorageError,
    TransientError,
)
from app.adapters.inbound.workers.tasks.face_clustering import update_clusters_task
from app.adapters.inbound.workers.service_container import get_services
from app.adapters.outbound.persistence.postgres import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.database import get_worker_session_context
from app.application.services import PhotoProcessingService
from app.domain.entities import Face
from app.domain.exceptions import EntityNotFoundException

logger = logging.getLogger(__name__)


def _get_photo_processing_service(session) -> PhotoProcessingService:
    """
    Create PhotoProcessingService instance with all dependencies.

    Args:
        session: Database session

    Returns:
        Configured PhotoProcessingService instance
    """
    photo_repo = PhotoRepositoryPostgres(session)
    face_repo = FaceRepositoryPostgres(session)

    # Get services from container (lazy-loaded singletons)
    services = get_services()

    return PhotoProcessingService(
        photo_repo=photo_repo,
        face_repo=face_repo,
        ml_services=services.ml_services,
        vector_store=services.vector_store,
        file_storage=services.file_storage,
    )


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
    name="photo_processing.process_photo",
    autoretry_for=(TransientError, OperationalError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def process_photo_task(self, photo_id: str) -> dict:
    """
    Process a photo: extract metadata, generate thumbnail, create CLIP embedding.

    Timeouts: 25 min soft, 30 min hard.

    This task automatically retries on transient errors (network issues, temporary
    database failures) with exponential backoff. Uses task execution tracking for
    idempotency - if the task completes successfully and is retried, it will detect
    the previous completion and skip processing.

    Args:
        photo_id: UUID of the photo to process

    Returns:
        Dictionary with processing results

    Raises:
        PermanentError: For errors that should not be retried
        TransientError: For temporary errors that will trigger retry
    """
    try:
        # Get task_id for idempotency tracking
        task_id = self.request.id
        return run_async(_process_photo_async(photo_id, task_id=task_id))
    except PermanentError:
        logger.error(
            f"Permanent error processing photo {photo_id}, will not retry",
            exc_info=True,
            extra={"photo_id": photo_id},
        )
        raise
    except TransientError as e:
        logger.warning(
            f"Transient error processing photo {photo_id}, will retry",
            extra={"photo_id": photo_id, "error": str(e), "retries": self.request.retries},
        )
        raise
    except Exception as e:
        # Unknown errors - log and convert to appropriate type
        logger.exception(
            f"Unexpected error processing photo {photo_id}",
            extra={"photo_id": photo_id},
        )
        # Don't retry unknown errors by default
        raise PermanentError(f"Unexpected error: {e!s}", {"photo_id": photo_id})


async def _process_photo_async(photo_id: str, task_id: Optional[str] = None) -> dict:
    """
    Async implementation of photo processing.

    Delegates to PhotoProcessingService for business logic.
    This function handles idempotency tracking and error translation.
    """
    try:
        photo_uuid = UUID(photo_id)
    except (ValueError, AttributeError):
        raise InvalidDataError(f"Invalid photo_id format: {photo_id}", {"photo_id": photo_id})

    try:
        async with get_worker_session_context() as session:
            # Import idempotency helpers
            from app.adapters.inbound.workers.idempotency import (
                check_task_completed,
                mark_task_completed,
                mark_task_running,
            )

            # Check idempotency if task_id provided
            if task_id:
                if await check_task_completed(session, task_id):
                    logger.info(f"Task {task_id} already completed, skipping")
                    return {"status": "already_completed", "photo_id": photo_id}

                # Mark task as running
                await mark_task_running(
                    session,
                    task_id,
                    "process_photo_task",
                    context={"photo_id": photo_id},
                )
                await session.commit()

            # Get service instance with session
            service = _get_photo_processing_service(session)

            # Delegate to service for business logic
            try:
                result = await service.process_photo(photo_uuid)
                await session.commit()

                # Mark task as completed for idempotency
                if task_id:
                    await mark_task_completed(
                        session,
                        task_id,
                        result=result.to_dict(),
                    )
                    await session.commit()

                return result.to_dict()

            except EntityNotFoundException:
                logger.error(f"Photo {photo_id} not found")
                raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})
            except ValueError as e:
                # Service raises ValueError for data/storage issues
                logger.error(f"Processing error for {photo_id}: {e}")
                raise ProcessingError(str(e), {"photo_id": photo_id})
            except Exception as e:
                # Catch-all for unexpected errors
                logger.error(f"Unexpected error processing {photo_id}: {e}", exc_info=True)
                raise TransientError(f"Processing failed: {e!s}", {"photo_id": photo_id})

    except SoftTimeLimitExceeded:
        logger.error(f"Task soft timeout for photo {photo_id}")
        # Compensating action: mark as timeout
        async with get_worker_session_context() as session:
            photo_repo = PhotoRepositoryPostgres(session)
            photo = await photo_repo.find_by_id(photo_uuid)
            if photo:
                photo.set_processing_status("timeout")
                await photo_repo.save(photo)
                await session.commit()
        raise
    except (OperationalError, DBAPIError) as e:
        logger.error(f"Database error during photo processing {photo_id}: {e}")
        raise DatabaseConnectionError(f"Database error: {e!s}", {"photo_id": photo_id})


@celery_app.task(
    bind=True,
    name="photo_processing.detect_faces",
    autoretry_for=(TransientError, OperationalError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def detect_faces_task(self, photo_id: str) -> dict:
    """
    Detect faces in a photo and store their embeddings.

    Timeouts: 25 min soft, 30 min hard.

    This task automatically retries on transient errors with exponential backoff.

    Args:
        photo_id: UUID of the photo

    Returns:
        Dictionary with detection results

    Raises:
        PermanentError: For errors that should not be retried
        TransientError: For temporary errors that will trigger retry
    """
    try:
        return run_async(_detect_faces_async(photo_id))
    except PermanentError:
        logger.error(
            f"Permanent error detecting faces in {photo_id}, will not retry",
            exc_info=True,
            extra={"photo_id": photo_id},
        )
        raise
    except TransientError as e:
        logger.warning(
            f"Transient error detecting faces in {photo_id}, will retry",
            extra={"photo_id": photo_id, "error": str(e), "retries": self.request.retries},
        )
        raise
    except Exception as e:
        logger.exception(
            f"Unexpected error detecting faces in {photo_id}",
            extra={"photo_id": photo_id},
        )
        raise PermanentError(f"Unexpected error: {e!s}", {"photo_id": photo_id})


async def _detect_faces_async(photo_id: str) -> dict:
    """
    Async implementation of face detection.

    Delegates to PhotoProcessingService for business logic.
    This function handles error translation and clustering triggers.
    """
    try:
        photo_uuid = UUID(photo_id)
    except (ValueError, AttributeError):
        raise InvalidDataError(f"Invalid photo_id format: {photo_id}", {"photo_id": photo_id})

    try:
        async with get_worker_session_context() as session:
            # Get service instance with session
            service = _get_photo_processing_service(session)

            # Delegate to service for business logic
            try:
                result = await service.detect_faces(photo_uuid)
                await session.commit()

                # Success: Trigger incremental clustering for newly detected faces
                if result.face_ids:
                    try:
                        update_clusters_task.delay(result.face_ids)
                        logger.debug(
                            f"Queued clustering task for {len(result.face_ids)} faces"
                        )
                    except Exception as e:
                        # Clustering trigger failure is non-critical
                        logger.warning(f"Failed to trigger clustering for {photo_id}: {e}")

                return result.to_dict()

            except EntityNotFoundException:
                logger.error(f"Photo {photo_id} not found")
                raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})
            except ValueError as e:
                # Service raises ValueError for data/storage issues
                logger.error(f"Face detection error for {photo_id}: {e}")
                raise ProcessingError(str(e), {"photo_id": photo_id})
            except Exception as e:
                # Catch-all for unexpected errors
                logger.error(
                    f"Unexpected error detecting faces in {photo_id}: {e}", exc_info=True
                )
                raise TransientError(f"Face detection failed: {e!s}", {"photo_id": photo_id})

    except SoftTimeLimitExceeded:
        logger.error(f"Task soft timeout for face detection on photo {photo_id}")
        # No specific cleanup needed - faces saved to DB are okay to keep
        # They will be picked up by clustering later
        raise
    except (OperationalError, DBAPIError) as e:
        logger.error(f"Database error during face detection {photo_id}: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Database error: {e!s}", {"photo_id": photo_id})


@celery_app.task(
    bind=True,
    name="photo_processing.reprocess_photo",
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def reprocess_photo_task(self, photo_id: str) -> dict:
    """
    Re-process an existing photo (regenerate embeddings, etc.).

    Timeouts: 25 min soft, 30 min hard.

    Args:
        photo_id: UUID of the photo

    Returns:
        Dictionary with processing results
    """
    # First process the photo
    result = process_photo_task(photo_id)
    if result.get("status") != "completed":
        return result

    # Then detect faces
    face_result = detect_faces_task(photo_id)
    return {
        "status": "completed",
        "photo_id": photo_id,
        "processing_result": result,
        "face_detection_result": face_result,
    }


@celery_app.task(
    bind=True,
    name="photo_processing.generate_embedding_from_thumbnail",
    autoretry_for=(TransientError, OperationalError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def generate_embedding_from_thumbnail_task(self, photo_id: str) -> dict:
    """
    Generate CLIP embedding from an existing thumbnail.

    Timeouts: 25 min soft, 30 min hard.

    This is useful for Google Photos where we only have thumbnails stored locally.
    Automatically retries on transient errors.

    Args:
        photo_id: UUID of the photo

    Returns:
        Dictionary with processing results
    """
    try:
        return run_async(_generate_embedding_from_thumbnail_async(photo_id))
    except PermanentError:
        logger.error(
            f"Permanent error generating embedding for {photo_id}",
            exc_info=True,
            extra={"photo_id": photo_id},
        )
        raise
    except TransientError as e:
        logger.warning(
            f"Transient error generating embedding for {photo_id}, will retry",
            extra={"photo_id": photo_id, "error": str(e), "retries": self.request.retries},
        )
        raise
    except Exception as e:
        logger.exception(
            f"Unexpected error generating embedding for {photo_id}", extra={"photo_id": photo_id}
        )
        raise PermanentError(f"Unexpected error: {e!s}", {"photo_id": photo_id})


async def _generate_embedding_from_thumbnail_async(photo_id: str) -> dict:
    """
    Async implementation of embedding generation from thumbnail with proper transaction boundaries.

    Transaction pattern:
    - Phase 1: Load photo and thumbnail path (read-only transaction)
    - Phase 2: Load thumbnail and generate embedding (outside transaction)
    - Phase 3: Store embedding in vector store (separate from DB)
    - Phase 4: Update photo status in DB and commit
    """
    photo_uuid = UUID(photo_id)

    # Get services from container (lazy-loaded singletons)
    services = get_services()
    ml_services = services.ml_services
    vector_store = services.vector_store
    file_storage = services.file_storage

    # Phase 1: Load photo and get thumbnail path (read-only transaction)
    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        photo = await photo_repo.find_by_id(photo_uuid)
        if not photo:
            logger.error(f"Photo {photo_id} not found")
            return {"status": "error", "message": "Photo not found"}

        if not photo.thumbnail_path:
            logger.error(f"Photo {photo_id} has no thumbnail")
            return {"status": "error", "message": "No thumbnail available"}

        thumbnail_path = photo.thumbnail_path
        filename = photo.filename
        connector_type = photo.connector_type

    # Phase 2: Load thumbnail and generate embedding (outside transaction)
    try:
        # Load thumbnail data
        image_data = await file_storage.get_file(thumbnail_path)
        if not image_data:
            logger.error(f"Could not load thumbnail for photo {photo_id}")
            return {"status": "error", "message": "Could not load thumbnail"}

        # Generate CLIP embedding
        embedding = await ml_services.encode_image(image_data)
        logger.debug(f"Generated embedding for photo {photo_id} from thumbnail")

    except Exception as e:
        logger.error(f"Error processing thumbnail for {photo_id}: {e}", exc_info=True)
        return {"status": "error", "message": f"Processing failed: {e!s}"}

    # Phase 3: Store embedding in vector store (separate from DB transaction)
    try:
        await vector_store.store_photo_embedding(
            photo_uuid,
            embedding,
            payload={
                "filename": filename,
                "connector_type": connector_type,
            },
        )
        logger.debug(f"Stored embedding for photo {photo_id} in vector store")

    except Exception as e:
        logger.error(
            f"Vector store error for {photo_id}: {e}",
            exc_info=True,
            extra={"photo_id": photo_id}
        )
        return {"status": "error", "message": f"Vector store failed: {e!s}"}

    # Phase 4: Update photo status in DB and commit
    try:
        async with get_worker_session_context() as session:
            photo_repo = PhotoRepositoryPostgres(session)

            photo = await photo_repo.find_by_id(photo_uuid)
            if not photo:
                logger.warning(f"Photo {photo_id} not found when updating status")
                return {"status": "error", "message": "Photo not found during update"}

            # Update photo status
            photo.set_processing_status("completed")
            await photo_repo.save(photo)
            await session.commit()

            logger.info(f"Generated embedding for photo {photo_id} from thumbnail")
            return {"status": "completed", "photo_id": photo_id}

    except Exception as e:
        logger.error(
            f"Database error updating photo {photo_id}: {e}",
            exc_info=True,
            extra={"photo_id": photo_id}
        )
        return {"status": "error", "message": f"Database update failed: {e!s}"}


@celery_app.task(
    bind=True,
    name="photo_processing.reprocess_connector_photos",
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def reprocess_connector_photos_task(self, connector_id: str) -> dict:
    """
    Reprocess all photos from a connector (generate embeddings from thumbnails).

    Timeouts: 25 min soft, 30 min hard.

    Args:
        connector_id: UUID of the connector

    Returns:
        Dictionary with processing results
    """
    return run_async(_reprocess_connector_photos_async(connector_id))


async def _reprocess_connector_photos_async(connector_id: str) -> dict:
    """Async implementation of connector photos reprocessing."""
    connector_uuid = UUID(connector_id)

    try:
        async with get_worker_session_context() as session:
            photo_repo = PhotoRepositoryPostgres(session)

            # Get all photos for this connector
            photos = await photo_repo.find_by_connector(connector_uuid, limit=10000)

            queued = 0
            for photo in photos:
                if photo.thumbnail_path:
                    # Queue embedding generation and face detection for each photo with thumbnail
                    generate_embedding_from_thumbnail_task.delay(str(photo.id.value))
                    detect_faces_task.delay(str(photo.id.value))
                    queued += 1

            logger.info(f"Queued {queued} photos for embedding generation and face detection")
            return {
                "status": "completed",
                "connector_id": connector_id,
                "total_photos": len(photos),
                "queued": queued,
            }
    except SoftTimeLimitExceeded:
        logger.error(f"Task soft timeout while reprocessing connector {connector_id}")
        # Partial queueing is acceptable - already queued tasks will proceed
        raise
