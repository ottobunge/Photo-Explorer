"""Photo processing tasks for background execution."""

import asyncio
import logging
from typing import Optional
from uuid import UUID

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
from app.adapters.outbound.ml import get_ml_services
from app.adapters.outbound.persistence.postgres import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.adapters.outbound.persistence.postgres.database import get_worker_session_context
from app.adapters.outbound.persistence.qdrant import QdrantVectorStore
from app.adapters.outbound.storage import LocalFileStorage
from app.domain.entities import Face

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
    """Async implementation of photo processing."""
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
        raise TransientError(f"Service initialization failed: {e!s}", {"photo_id": photo_id})

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

            photo_repo = PhotoRepositoryPostgres(session)

            # Get photo from database
            try:
                photo = await photo_repo.find_by_id(photo_uuid)
            except (OperationalError, DBAPIError) as e:
                logger.error(f"Database error fetching photo {photo_id}: {e}")
                raise DatabaseConnectionError(f"Database error: {e!s}", {"photo_id": photo_id})

            if not photo:
                logger.error(f"Photo {photo_id} not found")
                raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})

            # Phase 1: Update status to processing and commit
            try:
                photo.set_processing_status("processing")
                await photo_repo.save(photo)
                await session.commit()
                logger.debug(f"Photo {photo_id} marked as processing")
            except Exception as e:
                logger.error(f"Failed to update photo status: {e}")
                raise DatabaseConnectionError(f"Database error: {e!s}", {"photo_id": photo_id})

        # Phase 2: Load and process image (outside DB transaction)
        try:
            # Load image data
            image_data = None
            if photo.storage_path:
                try:
                    image_data = await file_storage.get_file(photo.storage_path)
                except (OSError, PermissionError) as e:
                    logger.error(f"Storage error loading photo {photo_id}: {e}")
                    raise StorageError(
                        f"Failed to load from storage: {e!s}", {"photo_id": photo_id}
                    )
            elif photo.source_path:
                try:
                    # For local connector, read from source path
                    with open(photo.source_path, "rb") as f:
                        image_data = f.read()
                except (OSError, PermissionError, FileNotFoundError) as e:
                    logger.error(f"File error loading photo {photo_id}: {e}")
                    raise StorageError(
                        f"Failed to load from source: {e!s}", {"photo_id": photo_id}
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
                    f"Thumbnail generation failed: {e!s}", {"photo_id": photo_id}
                )

            # Generate CLIP embedding
            embedding = None
            try:
                embedding = await ml_services.encode_image(image_data)
            except Exception as e:
                logger.error(f"Error generating embedding for {photo_id}: {e}")
                raise ProcessingError(
                    f"Embedding generation failed: {e!s}", {"photo_id": photo_id}
                )

            # Basic image analysis
            try:
                analysis = await ml_services.analyze_image(image_data)
                # Extract just the labels from DetectedObjectInfo for storage
                object_labels = [obj.label for obj in analysis.detected_objects]
                photo.set_ai_analysis(
                    description=analysis.description if analysis.description else None,
                    scene_classification=analysis.scene_classification,
                    detected_objects=object_labels,
                )
            except Exception as e:
                # Image analysis failure is non-critical, log and continue
                logger.warning(f"Image analysis failed for {photo_id}: {e}")

        except (PermanentError, TransientError, StorageError, ProcessingError) as e:
            # Compensating action: Mark photo as failed in database
            logger.error(f"Processing failed for photo {photo_id}, marking as failed")
            async with get_worker_session_context() as session:
                photo_repo = PhotoRepositoryPostgres(session)
                photo = await photo_repo.find_by_id(photo_uuid)
                if photo:
                    photo.set_processing_status("failed")
                    await photo_repo.save(photo)
                    await session.commit()
            raise

        # Phase 3: Store in vector store (separate from DB transaction)
        # If this fails, we'll retry the entire task, which is idempotent
        try:
            await vector_store.store_photo_embedding(
                photo.id.value,
                embedding,
                payload={
                    "filename": photo.filename,
                    "connector_type": photo.connector_type,
                },
            )
            logger.debug(f"Stored embedding for photo {photo_id}")
        except Exception as e:
            logger.error(f"Vector store error for {photo_id}: {e}")
            # Compensating action: Mark photo as failed
            async with get_worker_session_context() as session:
                photo_repo = PhotoRepositoryPostgres(session)
                photo = await photo_repo.find_by_id(photo_uuid)
                if photo:
                    photo.set_processing_status("failed")
                    await photo_repo.save(photo)
                    await session.commit()
            # Raise as transient error for retry
            raise TransientError(
                f"Vector store failed: {e!s}", {"photo_id": photo_id}
            )

        # Phase 4: Final commit - mark as completed
        async with get_worker_session_context() as session:
            try:
                photo_repo = PhotoRepositoryPostgres(session)
                photo = await photo_repo.find_by_id(photo_uuid)
                if not photo:
                    raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})

                # Mark as completed
                photo.set_processing_status("completed")
                await photo_repo.save(photo)

                # Mark task as completed for idempotency
                if task_id:
                    await mark_task_completed(
                        session,
                        task_id,
                        result={"photo_id": photo_id, "thumbnail_path": thumbnail_path},
                    )

                await session.commit()

                logger.info(f"Successfully processed photo {photo_id}")
                return {
                    "status": "completed",
                    "photo_id": photo_id,
                    "thumbnail_path": thumbnail_path,
                }

            except Exception as e:
                logger.error(f"Failed to mark photo as completed: {e}")
                raise DatabaseConnectionError(f"Database error: {e!s}", {"photo_id": photo_id})

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
    Async implementation of face detection with proper transaction boundaries.

    Transaction pattern:
    - Phase 1: Load photo and image data (read-only transaction)
    - Phase 2: Detect faces and process crops (outside transaction)
    - Phase 3: Save faces to DB and commit
    - Phase 4: Store embeddings in vector store (with compensation on failure)
    """
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
        raise TransientError(f"Service initialization failed: {e!s}", {"photo_id": photo_id})

    try:
        # Phase 1: Load photo and image data (read-only transaction)
        async with get_worker_session_context() as session:
            photo_repo = PhotoRepositoryPostgres(session)

            # Get photo
            try:
                photo = await photo_repo.find_by_id(photo_uuid)
            except (OperationalError, DBAPIError) as e:
                logger.error(f"Database error fetching photo {photo_id}: {e}")
                raise DatabaseConnectionError(f"Database error: {e!s}", {"photo_id": photo_id})

            if not photo:
                raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})

            # Store paths for later use
            storage_path = photo.storage_path
            source_path = photo.source_path

        # Phase 2: Load and process image (outside DB transaction)
        try:
            # Load image data
            image_data = None
            if storage_path:
                try:
                    image_data = await file_storage.get_file(storage_path)
                except (OSError, PermissionError) as e:
                    logger.error(f"Storage error loading photo {photo_id}: {e}", exc_info=True)
                    raise StorageError(
                        f"Failed to load from storage: {e!s}", {"photo_id": photo_id}
                    )
            elif source_path:
                try:
                    with open(source_path, "rb") as f:
                        image_data = f.read()
                except (OSError, PermissionError, FileNotFoundError) as e:
                    logger.error(f"File error loading photo {photo_id}: {e}", exc_info=True)
                    raise StorageError(
                        f"Failed to load from source: {e!s}", {"photo_id": photo_id}
                    )
            else:
                raise InvalidDataError("No image path available", {"photo_id": photo_id})

            if not image_data:
                raise ProcessingError("Could not load image data", {"photo_id": photo_id})

            # Detect faces using ML service
            try:
                detected_faces = await ml_services.detect_faces(image_data)
                logger.debug(f"Detected {len(detected_faces)} faces in photo {photo_id}")
            except Exception as e:
                logger.error(f"Face detection failed for {photo_id}: {e}", exc_info=True)
                raise ProcessingError(
                    f"Face detection failed: {e!s}", {"photo_id": photo_id}
                )

            # Process each detected face (generate crops)
            face_data = []  # List of (Face, embedding, crop_path)
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

                    # Store for batch processing
                    face_data.append((face, detected.embedding, crop_path))
                    logger.debug(
                        f"Processed face {face.id.value} from photo {photo_id} "
                        f"(confidence: {detected.detection_confidence:.2f})"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to process one detected face in {photo_id}: {e}",
                        exc_info=True,
                        extra={"photo_id": photo_id, "bbox": detected.bbox}
                    )
                    # Continue with other faces even if one fails

        except (PermanentError, TransientError, StorageError, ProcessingError) as e:
            # These errors should propagate immediately
            logger.error(
                f"Face processing failed for photo {photo_id}",
                extra={"photo_id": photo_id, "error": str(e)}
            )
            raise

        # Phase 3: Save all faces to database and commit
        saved_face_ids = []
        try:
            async with get_worker_session_context() as session:
                photo_repo = PhotoRepositoryPostgres(session)
                face_repo = FaceRepositoryPostgres(session)

                # Re-fetch photo in new transaction
                photo = await photo_repo.find_by_id(photo_uuid)
                if not photo:
                    raise ResourceNotFoundError("Photo not found", {"photo_id": photo_id})

                # Batch save all faces to database (single DB round-trip)
                if face_data:
                    faces_to_save = [face for face, _, _ in face_data]
                    try:
                        saved_faces = await face_repo.save_faces_batch(faces_to_save)

                        # Add all faces to photo
                        for saved_face in saved_faces:
                            photo.add_face(saved_face.id.value)
                            saved_face_ids.append(str(saved_face.id.value))

                        logger.debug(
                            f"Batch saved {len(saved_faces)} faces for photo {photo_id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to batch save faces to database: {e}",
                            exc_info=True,
                            extra={"photo_id": photo_id}
                        )
                        raise

                # Update photo with face references
                await photo_repo.save(photo)

                # Commit database transaction
                await session.commit()
                logger.info(
                    f"Saved {len(saved_face_ids)} faces to database for photo {photo_id}"
                )

        except Exception as e:
            logger.error(
                f"Database error saving faces for {photo_id}: {e}",
                exc_info=True,
                extra={"photo_id": photo_id}
            )
            raise DatabaseConnectionError(
                f"Failed to save faces to database: {e!s}", {"photo_id": photo_id}
            )

        # Phase 4: Store embeddings in vector store in batch (separate from DB transaction)
        # If this fails, we need to mark faces for reprocessing or delete orphaned DB records
        vector_store_face_ids = []
        try:
            # Prepare batch embeddings for faces that were successfully saved
            embeddings_batch = []
            for face, embedding, crop_path in face_data:
                face_id_str = str(face.id.value)
                if face_id_str in saved_face_ids:
                    embeddings_batch.append((
                        face.id.value,
                        embedding,
                        {"photo_id": str(photo_uuid), "cluster_id": None},
                    ))
                    vector_store_face_ids.append(face_id_str)

            # Batch store all embeddings (single vector store operation)
            if embeddings_batch:
                try:
                    await vector_store.store_face_embeddings_batch(embeddings_batch)
                    logger.info(
                        f"Batch stored {len(embeddings_batch)} face embeddings for photo {photo_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to batch store face embeddings: {e}",
                        exc_info=True,
                        extra={"photo_id": photo_id}
                    )
                    # Clear vector_store_face_ids on batch failure
                    vector_store_face_ids = []

            # Check if all embeddings were stored successfully
            if len(vector_store_face_ids) < len(saved_face_ids):
                failed_count = len(saved_face_ids) - len(vector_store_face_ids)
                logger.warning(
                    f"Vector store incomplete: {failed_count}/{len(saved_face_ids)} embeddings failed for {photo_id}",
                    extra={
                        "photo_id": photo_id,
                        "saved_faces": len(saved_face_ids),
                        "vector_store_faces": len(vector_store_face_ids),
                    }
                )
                # TODO: In future, could mark specific faces as needing reprocessing
                # For now, we keep the DB records and successfully stored embeddings

        except Exception as e:
            logger.error(
                f"Critical vector store error for {photo_id}: {e}",
                exc_info=True,
                extra={"photo_id": photo_id}
            )
            # Compensating action: Delete faces from database since vector store failed
            # This prevents orphaned records
            try:
                async with get_worker_session_context() as session:
                    photo_repo = PhotoRepositoryPostgres(session)
                    face_repo = FaceRepositoryPostgres(session)

                    photo = await photo_repo.find_by_id(photo_uuid)
                    if photo:
                        # Remove face references from photo
                        for face_id in saved_face_ids:
                            try:
                                photo.remove_face(UUID(face_id))
                            except (ValueError, AttributeError):
                                pass

                        await photo_repo.save(photo)

                        # Delete face records
                        for face_id in saved_face_ids:
                            try:
                                await face_repo.delete_face(UUID(face_id))
                                logger.debug(f"Deleted orphaned face {face_id} from database")
                            except Exception as del_error:
                                logger.warning(f"Failed to delete orphaned face {face_id}: {del_error}")

                        await session.commit()
                        logger.info(
                            f"Compensating action: Deleted {len(saved_face_ids)} faces from database after vector store failure",
                            extra={"photo_id": photo_id, "deleted_faces": saved_face_ids}
                        )
            except Exception as comp_error:
                logger.error(
                    f"Compensating action failed for {photo_id}: {comp_error}",
                    exc_info=True,
                    extra={"photo_id": photo_id}
                )

            # Raise transient error to trigger retry
            raise TransientError(
                f"Vector store failed, compensating action executed: {e!s}",
                {"photo_id": photo_id}
            )

        # Success: Trigger incremental clustering for newly detected faces
        if vector_store_face_ids:
            try:
                update_clusters_task.delay(vector_store_face_ids)
                logger.debug(f"Queued clustering task for {len(vector_store_face_ids)} faces")
            except Exception as e:
                # Clustering trigger failure is non-critical
                logger.warning(f"Failed to trigger clustering for {photo_id}: {e}")

        logger.info(
            f"Successfully detected and processed {len(vector_store_face_ids)} faces in photo {photo_id}",
            extra={
                "photo_id": photo_id,
                "faces_detected": len(detected_faces),
                "faces_saved": len(saved_face_ids),
                "faces_in_vector_store": len(vector_store_face_ids),
            }
        )
        return {
            "status": "completed",
            "photo_id": photo_id,
            "faces_detected": len(detected_faces),
            "faces_saved": len(saved_face_ids),
            "faces_in_vector_store": len(vector_store_face_ids),
            "face_ids": vector_store_face_ids,
        }

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

    ml_services = get_ml_services()  # Use singleton to avoid reloading models
    vector_store = QdrantVectorStore()
    file_storage = LocalFileStorage()

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
