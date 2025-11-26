"""Enhanced photo analysis tasks using vision models."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.inbound.workers.exceptions import TransientError
from app.adapters.outbound.ml import get_ml_services
from app.adapters.outbound.persistence.postgres import PhotoRepositoryPostgres
from app.adapters.outbound.persistence.postgres.database import get_worker_session_context
from app.adapters.outbound.storage import LocalFileStorage

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
    name="photo_analysis.analyze_photo",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def analyze_photo_task(self, photo_id: str) -> dict:
    """
    Run full photo analysis including description, objects, and scene.

    Timeouts: 25 min soft, 30 min hard.

    This task runs the vision LLM to generate descriptions,
    DETR for object detection, and scene classification.

    Args:
        photo_id: UUID of the photo to analyze

    Returns:
        Dictionary with analysis results
    """
    return run_async(_analyze_photo_async(photo_id))


async def _analyze_photo_async(photo_id: str) -> dict:
    """Async implementation of photo analysis."""
    photo_uuid = UUID(photo_id)

    # Use singleton ML services to avoid reloading models
    ml_services = get_ml_services()
    file_storage = LocalFileStorage()

    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        # Get photo
        photo = await photo_repo.find_by_id(photo_uuid)
        if not photo:
            return {"status": "error", "message": "Photo not found"}

        # Get photo bytes
        image_bytes = None
        if photo.storage_path:
            try:
                image_bytes = await file_storage.get_photo(photo.id.value)
            except Exception as e:
                logger.warning(f"Could not load from storage: {e}")

        if not image_bytes and photo.source_path:
            try:
                import aiofiles

                async with aiofiles.open(photo.source_path, "rb") as f:
                    image_bytes = await f.read()
            except Exception as e:
                logger.warning(f"Could not load from source: {e}")

        if not image_bytes:
            return {"status": "error", "message": "Could not load photo bytes"}

        try:
            # Run full analysis
            analysis = await ml_services.analyze_image(image_bytes)

            # Update photo with analysis results
            photo.description = analysis.description
            photo.scene_type = analysis.scene_classification.scene_type
            photo.scene_confidence = analysis.scene_classification.confidence
            photo.is_indoor = analysis.scene_classification.is_indoor

            # Store detected objects as JSON
            photo.detected_objects = [
                {
                    "label": obj.label,
                    "confidence": obj.confidence,
                    "bbox": {
                        "x": obj.bbox.x,
                        "y": obj.bbox.y,
                        "width": obj.bbox.width,
                        "height": obj.bbox.height,
                    },
                }
                for obj in analysis.detected_objects
            ]

            await photo_repo.save(photo)

            logger.info(
                f"Analyzed photo {photo_id}: {analysis.description[:50] if analysis.description else 'No description'}..."
            )

            return {
                "status": "completed",
                "photo_id": photo_id,
                "description": analysis.description,
                "scene_type": analysis.scene_classification.scene_type,
                "is_indoor": analysis.scene_classification.is_indoor,
                "objects_count": len(analysis.detected_objects),
            }

        except Exception as e:
            logger.exception(f"Error analyzing photo {photo_id}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="photo_analysis.generate_description",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def generate_description_task(self, photo_id: str, prompt: str = None) -> dict:
    """
    Generate a description for a photo using vision LLM.

    Timeouts: 25 min soft, 30 min hard.

    Args:
        photo_id: UUID of the photo
        prompt: Optional custom prompt for description generation

    Returns:
        Dictionary with generated description
    """
    return run_async(_generate_description_async(photo_id, prompt))


async def _generate_description_async(photo_id: str, prompt: str = None) -> dict:
    """Async implementation of description generation."""
    photo_uuid = UUID(photo_id)

    # Use singleton ML services
    ml_services = get_ml_services()
    file_storage = LocalFileStorage()

    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        photo = await photo_repo.find_by_id(photo_uuid)
        if not photo:
            return {"status": "error", "message": "Photo not found"}

        # Get photo bytes
        image_bytes = None
        if photo.storage_path:
            try:
                image_bytes = await file_storage.get_photo(photo.id.value)
            except Exception:
                pass

        if not image_bytes and photo.source_path:
            try:
                import aiofiles

                async with aiofiles.open(photo.source_path, "rb") as f:
                    image_bytes = await f.read()
            except Exception:
                pass

        if not image_bytes:
            return {"status": "error", "message": "Could not load photo bytes"}

        try:
            description = await ml_services.generate_description(image_bytes, prompt)

            # Update photo
            photo.description = description
            await photo_repo.save(photo)

            return {
                "status": "completed",
                "photo_id": photo_id,
                "description": description,
            }

        except Exception as e:
            logger.exception(f"Error generating description for {photo_id}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="photo_analysis.answer_question",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def answer_question_task(self, photo_id: str, question: str) -> dict:
    """
    Answer a question about a photo using visual question answering.

    Timeouts: 25 min soft, 30 min hard.

    Args:
        photo_id: UUID of the photo
        question: Question to answer

    Returns:
        Dictionary with the answer
    """
    return run_async(_answer_question_async(photo_id, question))


async def _answer_question_async(photo_id: str, question: str) -> dict:
    """Async implementation of question answering."""
    photo_uuid = UUID(photo_id)

    # Use singleton ML services
    ml_services = get_ml_services()
    file_storage = LocalFileStorage()

    async with get_worker_session_context() as session:
        photo_repo = PhotoRepositoryPostgres(session)

        photo = await photo_repo.find_by_id(photo_uuid)
        if not photo:
            return {"status": "error", "message": "Photo not found"}

        # Get photo bytes
        image_bytes = None
        if photo.storage_path:
            try:
                image_bytes = await file_storage.get_photo(photo.id.value)
            except Exception:
                pass

        if not image_bytes and photo.source_path:
            try:
                import aiofiles

                async with aiofiles.open(photo.source_path, "rb") as f:
                    image_bytes = await f.read()
            except Exception:
                pass

        if not image_bytes:
            return {"status": "error", "message": "Could not load photo bytes"}

        try:
            answer = await ml_services.answer_question(image_bytes, question)

            return {
                "status": "completed",
                "photo_id": photo_id,
                "question": question,
                "answer": answer,
            }

        except Exception as e:
            logger.exception(f"Error answering question for {photo_id}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    name="photo_analysis.batch_analyze",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def batch_analyze_task(self, photo_ids: list[str]) -> dict:
    """
    Analyze multiple photos in batch.

    Timeouts: 25 min soft, 30 min hard.

    Args:
        photo_ids: List of photo UUIDs to analyze

    Returns:
        Dictionary with batch results
    """
    results = {
        "total": len(photo_ids),
        "completed": 0,
        "failed": 0,
        "errors": [],
    }

    for photo_id in photo_ids:
        result = analyze_photo_task(photo_id)
        if result.get("status") == "completed":
            results["completed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(
                {
                    "photo_id": photo_id,
                    "error": result.get("message", "Unknown error"),
                }
            )

    return results


@celery_app.task(
    name="photo_analysis.analyze_pending_photos",
    autoretry_for=(TransientError, OperationalError, ConnectionError, OSError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},  # Fewer retries for scheduled task
)
def analyze_pending_photos() -> dict:
    """
    Analyze all photos that haven't been analyzed yet.

    This is a scheduled task that processes photos without descriptions.
    """
    return run_async(_analyze_pending_photos_async())


async def _analyze_pending_photos_async() -> dict:
    """Find and queue analysis for pending photos."""
    async with get_worker_session_context() as session:
        # Find photos without descriptions
        # Note: This would need a custom repository method
        # For now, we'll use a placeholder approach
        from sqlalchemy import select

        from app.adapters.outbound.persistence.postgres.models import PhotoModel

        stmt = (
            select(PhotoModel)
            .where(
                PhotoModel.description.is_(None),
                PhotoModel.processing_status == "completed",
            )
            .limit(100)
        )

        result = await session.execute(stmt)
        photos = result.scalars().all()

        queued = 0
        for photo in photos:
            analyze_photo_task.delay(str(photo.id))
            queued += 1

        logger.info(f"Queued {queued} photos for analysis")
        return {"status": "completed", "queued": queued}
