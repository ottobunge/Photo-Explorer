"""Photo processing tasks for background execution."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy.exc import DBAPIError, OperationalError

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.inbound.workers.exceptions import (
    DatabaseConnectionError,
    InvalidDataError,
    NetworkError,
    PermanentError,
    ProcessingError,
    ResourceNotFoundError,
    StorageError,
    TransientError,
)
from app.adapters.outbound.ml import MLServicesAdapter, get_ml_services
from app.adapters.outbound.persistence.postgres import (
    PhotoRepositoryPostgres,
    FaceRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.database import get_worker_session_context
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.adapters.outbound.storage import LocalFileStorage
from app.domain.entities import Face
from app.domain.value_objects import FaceId
from app.adapters.inbound.workers.tasks.face_clustering import update_clusters_task

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
    name="photo_processing.process_photo",
    autoretry_for=(TransientError, OperationalError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
)
def process_photo_task(self, photo_id: str) -> dict:
    """
    Process a photo: extract metadata, generate thumbnail, create CLIP embedding.

    This task automatically retries on transient errors (network issues, temporary
    database failures) with exponential backoff.

    Args:
        photo_id: UUID of the photo to process

    Returns:
        Dictionary with processing results

    Raises:
        PermanentError: For errors that should not be retried
        TransientError: For temporary errors that will trigger retry
    """
    try:
        return run_async(_process_photo_async(photo_id))
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
        raise PermanentError(f"Unexpected error: {str(e)}", {"photo_id": photo_id})


async def _process_photo_async(photo_id: str) -> dict:
    """Async implementation of photo processing."""
    try:
        photo_uuid = UUID(photo_id)
    except (ValueError, AttributeError) as e:
        raise InvalidDataError(f"Invalid photo_id format: {photo_id}", {"photo_id": photo_id})

    # Initialize services - use singleton for ML services
    try:
        ml_services = get_ml_services()
        vector_store = QdrantVectorStore()
        file_storage = LocalFileStorage()
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise TransientError(f"Service initialization failed: {str(e)}", {"photo_id": photo_id})

    try:
        async with get_worker_session_context() as session:
            photo_repo = PhotoRepositoryPostgres(session)

            # Get photo from database
            try:
                photo = await photo_repo.find_by_id(photo_uuid)
            except (OperationalError, DBAPIError) as e:
                logger.error(f"Database error fetching photo {photo_id}: {e}")
                raise DatabaseConnectionError(f"Database error: {str(e)}", {"photo_id": photo_id})

            if not photo:
                logger.error(f"Photo {photo_id} not found")
                raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})

            try:
                # Update status to processing
                photo.set_processing_status("processing")
                await photo_repo.save(photo)

                # Load image data
                image_data = None
                if photo.storage_path:
                    try:
                        image_data = await file_storage.get_file(photo.storage_path)
                    except (IOError, OSError, PermissionError) as e:
                        logger.error(f"Storage error loading photo {photo_id}: {e}")
                        raise StorageError(
                            f"Failed to load from storage: {str(e)}", {"photo_id": photo_id}
                        )
                elif photo.source_path:
                    try:
                        # For local connector, read from source path
                        with open(photo.source_path, "rb") as f:
                            image_data = f.read()
                    except (IOError, OSError, PermissionError, FileNotFoundError) as e:
                        logger.error(f"File error loading photo {photo_id}: {e}")
                        raise StorageError(
                            f"Failed to load from source: {str(e)}", {"photo_id": photo_id}
                        )
                else:
                    raise InvalidDataError("No image path available", {"photo_id": photo_id})

                if not image_data:
                    raise ProcessingError("Could not load image data", {"photo_id": photo_id})

                # Generate thumbnail
                try:
                    thumbnail_data = await ml_services.generate_thumbnail(image_data)
                    thumbnail_path = await file_storage.save_thumbnail(
                        thumbnail_data, str(photo.id.value)
                    )
                    photo.thumbnail_path = thumbnail_path
                except Exception as e:
                    logger.error(f"Error generating thumbnail for {photo_id}: {e}")
                    raise ProcessingError(
                        f"Thumbnail generation failed: {str(e)}", {"photo_id": photo_id}
                    )

                # Generate CLIP embedding
                try:
                    embedding = await ml_services.encode_image(image_data)
                    await vector_store.store_photo_embedding(
                        photo.id.value,
                        embedding,
                        payload={
                            "filename": photo.filename,
                            "connector_type": photo.connector_type,
                        },
                    )
                except Exception as e:
                    logger.error(f"Error generating embedding for {photo_id}: {e}")
                    # Embedding failure might be transient (vector store down)
                    raise TransientError(
                        f"Embedding generation failed: {str(e)}", {"photo_id": photo_id}
                    )

                # Basic image analysis
                try:
                    analysis = await ml_services.analyze_image(image_data)
                    photo.set_ai_analysis(
                        description=analysis.description if analysis.description else None,
                        scene_classification=analysis.scene_classification,
                        detected_objects=analysis.detected_objects,
                    )
                except Exception as e:
                    # Image analysis failure is non-critical, log and continue
                    logger.warning(f"Image analysis failed for {photo_id}: {e}")

                # Mark as completed
                photo.set_processing_status("completed")
                await photo_repo.save(photo)

                logger.info(f"Successfully processed photo {photo_id}")
                return {
                    "status": "completed",
                    "photo_id": photo_id,
                    "thumbnail_path": thumbnail_path,
                }

            except (PermanentError, TransientError):
                # Re-raise our custom errors
                photo.set_processing_status("failed")
                try:
                    await photo_repo.save(photo)
                except Exception as save_err:
                    logger.error(f"Failed to save error status for photo {photo_id}: {save_err}")
                raise
            except Exception as e:
                # Catch-all for unexpected errors
                logger.exception(f"Unexpected error processing photo {photo_id}: {e}")
                photo.set_processing_status("failed")
                try:
                    await photo_repo.save(photo)
                except Exception as save_err:
                    logger.error(f"Failed to save error status for photo {photo_id}: {save_err}")
                raise ProcessingError(
                    f"Unexpected processing error: {str(e)}", {"photo_id": photo_id}
                )

    except (OperationalError, DBAPIError) as e:
        logger.error(f"Database error during photo processing {photo_id}: {e}")
        raise DatabaseConnectionError(f"Database error: {str(e)}", {"photo_id": photo_id})


@celery_app.task(
    bind=True,
    name="photo_processing.detect_faces",
    autoretry_for=(TransientError, OperationalError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_backoff_max=600,
)
def detect_faces_task(self, photo_id: str) -> dict:
    """
    Detect faces in a photo and store their embeddings.

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
        raise PermanentError(f"Unexpected error: {str(e)}", {"photo_id": photo_id})


async def _detect_faces_async(photo_id: str) -> dict:
    """Async implementation of face detection."""
    try:
        photo_uuid = UUID(photo_id)
    except (ValueError, AttributeError):
        raise InvalidDataError(f"Invalid photo_id format: {photo_id}", {"photo_id": photo_id})

    # Initialize services - use singleton for ML services
    try:
        ml_services = get_ml_services()
        vector_store = QdrantVectorStore()
        file_storage = LocalFileStorage()
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise TransientError(f"Service initialization failed: {str(e)}", {"photo_id": photo_id})

    try:
        async with get_worker_session_context() as session:
            photo_repo = PhotoRepositoryPostgres(session)
            face_repo = FaceRepositoryPostgres(session)

            # Get photo
            try:
                photo = await photo_repo.find_by_id(photo_uuid)
            except (OperationalError, DBAPIError) as e:
                logger.error(f"Database error fetching photo {photo_id}: {e}")
                raise DatabaseConnectionError(f"Database error: {str(e)}", {"photo_id": photo_id})

            if not photo:
                raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})

            try:
                # Load image data
                image_data = None
                if photo.storage_path:
                    try:
                        image_data = await file_storage.get_file(photo.storage_path)
                    except (IOError, OSError, PermissionError) as e:
                        logger.error(f"Storage error loading photo {photo_id}: {e}")
                        raise StorageError(
                            f"Failed to load from storage: {str(e)}", {"photo_id": photo_id}
                        )
                elif photo.source_path:
                    try:
                        with open(photo.source_path, "rb") as f:
                            image_data = f.read()
                    except (IOError, OSError, PermissionError, FileNotFoundError) as e:
                        logger.error(f"File error loading photo {photo_id}: {e}")
                        raise StorageError(
                            f"Failed to load from source: {str(e)}", {"photo_id": photo_id}
                        )
                else:
                    raise InvalidDataError("No image path available", {"photo_id": photo_id})

                if not image_data:
                    raise ProcessingError("Could not load image data", {"photo_id": photo_id})

                # Detect faces
                try:
                    detected_faces = await ml_services.detect_faces(image_data)
                except Exception as e:
                    logger.error(f"Face detection failed for {photo_id}: {e}")
                    raise ProcessingError(
                        f"Face detection failed: {str(e)}", {"photo_id": photo_id}
                    )

                face_ids = []
                for detected in detected_faces:
                    try:
                        # Create Face entity
                        face = Face.create(
                            photo_id=photo_uuid,
                            bbox=detected.bbox,
                            quality_score=detected.quality_score,
                            detection_confidence=detected.detection_confidence,
                        )

                        # Generate and save face crop
                        crop_data = await ml_services.crop_face(image_data, detected.bbox)
                        crop_path = await file_storage.save_face_crop(crop_data, str(face.id.value))
                        face.set_crop_path(crop_path)

                        # Save face to database
                        face = await face_repo.save_face(face)

                        # Store face embedding in vector store
                        await vector_store.store_face_embedding(
                            face.id.value,
                            detected.embedding,
                            payload={
                                "photo_id": str(photo_uuid),
                                "cluster_id": None,
                            },
                        )

                        # Add face to photo
                        photo.add_face(face.id.value)
                        face_ids.append(str(face.id.value))
                    except Exception as e:
                        logger.error(f"Error processing detected face in {photo_id}: {e}")
                        # Continue with other faces even if one fails

                await photo_repo.save(photo)

                # Trigger incremental clustering for newly detected faces
                if face_ids:
                    update_clusters_task.delay()

                logger.info(f"Detected {len(face_ids)} faces in photo {photo_id}")
                return {
                    "status": "completed",
                    "photo_id": photo_id,
                    "faces_detected": len(face_ids),
                    "face_ids": face_ids,
                }

            except (PermanentError, TransientError):
                # Re-raise our custom errors
                raise
            except Exception as e:
                logger.exception(f"Unexpected error detecting faces in {photo_id}: {e}")
                raise ProcessingError(
                    f"Unexpected face detection error: {str(e)}", {"photo_id": photo_id}
                )

    except (OperationalError, DBAPIError) as e:
        logger.error(f"Database error during face detection {photo_id}: {e}")
        raise DatabaseConnectionError(f"Database error: {str(e)}", {"photo_id": photo_id})


@celery_app.task(bind=True, name="photo_processing.reprocess_photo")
def reprocess_photo_task(self, photo_id: str) -> dict:
    """
    Re-process an existing photo (regenerate embeddings, etc.).

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
)
def generate_embedding_from_thumbnail_task(self, photo_id: str) -> dict:
    """
    Generate CLIP embedding from an existing thumbnail.

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
        raise PermanentError(f"Unexpected error: {str(e)}", {"photo_id": photo_id})


async def _generate_embedding_from_thumbnail_async(photo_id: str) -> dict:
    """Async implementation of embedding generation from thumbnail."""
    photo_uuid = UUID(photo_id)

    ml_services = get_ml_services()  # Use singleton to avoid reloading models
    vector_store = QdrantVectorStore()
    file_storage = LocalFileStorage()

    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        photo = await photo_repo.find_by_id(photo_uuid)
        if not photo:
            return {"status": "error", "message": "Photo not found"}

        if not photo.thumbnail_path:
            return {"status": "error", "message": "No thumbnail available"}

        try:
            # Load thumbnail data
            image_data = await file_storage.get_file(photo.thumbnail_path)
            if not image_data:
                return {"status": "error", "message": "Could not load thumbnail"}

            # Generate CLIP embedding
            embedding = await ml_services.encode_image(image_data)
            await vector_store.store_photo_embedding(
                photo.id.value,
                embedding,
                payload={
                    "filename": photo.filename,
                    "connector_type": photo.connector_type,
                },
            )

            # Update photo status
            photo.set_processing_status("completed")
            await photo_repo.save(photo)

            logger.info(f"Generated embedding for photo {photo_id} from thumbnail")
            return {"status": "completed", "photo_id": photo_id}

        except Exception as e:
            logger.exception(f"Error generating embedding for {photo_id}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="photo_processing.reprocess_connector_photos")
def reprocess_connector_photos_task(self, connector_id: str) -> dict:
    """
    Reprocess all photos from a connector (generate embeddings from thumbnails).

    Args:
        connector_id: UUID of the connector

    Returns:
        Dictionary with processing results
    """
    return run_async(_reprocess_connector_photos_async(connector_id))


async def _reprocess_connector_photos_async(connector_id: str) -> dict:
    """Async implementation of connector photos reprocessing."""
    connector_uuid = UUID(connector_id)

    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        # Get all photos for this connector
        photos = await photo_repo.find_by_connector(connector_uuid, limit=10000)

        queued = 0
        for photo in photos:
            if photo.thumbnail_path:
                # Queue embedding generation for each photo with thumbnail
                generate_embedding_from_thumbnail_task.delay(str(photo.id.value))
                queued += 1

        logger.info(f"Queued {queued} photos for embedding generation")
        return {
            "status": "completed",
            "connector_id": connector_id,
            "total_photos": len(photos),
            "queued": queued,
        }
