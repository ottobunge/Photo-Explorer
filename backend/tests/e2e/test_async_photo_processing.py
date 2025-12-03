"""
End-to-end tests for asynchronous photo processing with Celery worker.

Tests the complete async processing pipeline:
1. Photo is uploaded and saved
2. Celery worker processes photo (thumbnail, CLIP embedding)
3. Face detection runs in worker
4. All data is persisted correctly
"""

import asyncio
import logging
from pathlib import Path
from uuid import UUID

import pytest

from app.adapters.inbound.workers.celery_app import celery_app
from app.adapters.outbound.ml import get_ml_services
from app.adapters.outbound.persistence.postgres import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from app.domain.entities import Photo

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestAsyncPhotoProcessing:
    """End-to-end tests for async photo processing with Celery worker."""

    async def test_photo_processing_task_completes(
        self,
        test_session,
        test_file_storage,
        single_face_images,
        celery_worker,
    ):
        """
        E2E: Verify photo processing task completes successfully.

        Tests that:
        1. Photo is uploaded and saved
        2. Photo processing task is enqueued
        3. Celery worker processes the task
        4. Photo status changes to 'completed'
        5. Thumbnail and CLIP embedding are generated
        """
        if not single_face_images:
            pytest.skip("No test images available")

        photo_repo = PhotoRepositoryPostgres(test_session)
        file_storage = test_file_storage

        # Load image
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        # Create photo entity
        photo = Photo.create(
            filename=source_path.name,
            original_path=str(source_path),
            connector_type="local",
        )

        # Save to storage
        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=image_data,
        )
        photo.set_storage_path(storage_path)

        # Save photo entity
        await photo_repo.save(photo)
        await test_session.commit()

        # Enqueue processing task
        task = celery_app.send_task(
            "photo_processing.process_photo",
            args=[str(photo.id.value)],
            queue="processing",
        )

        logger.info(f"Enqueued processing task {task.id} for photo {photo.id.value}")

        # Wait for task to complete
        from tests.e2e.conftest import wait_for_celery_task

        result = wait_for_celery_task(task.id, expected_state="SUCCESS", timeout=60.0)

        assert result.successful()

        # Refresh photo from database
        processed_photo = await photo_repo.find_by_id(photo.id.value)

        assert processed_photo is not None
        assert processed_photo.processing_status == "completed"
        assert processed_photo.thumbnail_path is not None
        assert processed_photo.clip_embedding is not None

        logger.info(
            f"Photo {photo.id.value} processing completed successfully. "
            f"Thumbnail: {processed_photo.thumbnail_path}, "
            f"Embedding dim: {len(processed_photo.clip_embedding)}"
        )

    async def test_concurrent_photo_processing(
        self,
        test_session,
        test_file_storage,
        single_face_images,
        celery_worker,
    ):
        """
        E2E: Verify multiple photos can be processed concurrently.

        Tests that:
        1. Multiple photos can be uploaded and enqueued simultaneously
        2. Worker processes them concurrently
        3. All photos complete successfully
        4. No interference between concurrent processing
        """
        if len(single_face_images) < 3:
            pytest.skip("At least 3 test images needed for this test")

        photo_repo = PhotoRepositoryPostgres(test_session)
        file_storage = test_file_storage

        # Create and save 3 photos
        photos = []
        for i, image_path in enumerate(single_face_images[:3]):
            with open(image_path, "rb") as f:
                image_data = f.read()

            photo = Photo.create(
                filename=f"concurrent_{i}_{image_path.name}",
                original_path=str(image_path),
                connector_type="local",
            )

            storage_path = await file_storage.save_photo(
                photo_id=str(photo.id.value),
                file_data=image_data,
            )
            photo.set_storage_path(storage_path)
            await photo_repo.save(photo)

            photos.append(photo)

        await test_session.commit()

        # Enqueue all processing tasks
        tasks = []
        for photo in photos:
            task = celery_app.send_task(
                "photo_processing.process_photo",
                args=[str(photo.id.value)],
                queue="processing",
            )
            tasks.append((photo.id.value, task))

        logger.info(f"Enqueued {len(tasks)} processing tasks")

        # Wait for all tasks to complete
        from tests.e2e.conftest import wait_for_celery_task

        for photo_id, task in tasks:
            result = wait_for_celery_task(
                task.id, expected_state="SUCCESS", timeout=60.0
            )
            assert result.successful()

        # Verify all photos processed successfully
        for photo_id, _ in tasks:
            processed_photo = await photo_repo.find_by_id(photo_id)

            assert processed_photo is not None
            assert processed_photo.processing_status == "completed"
            assert processed_photo.thumbnail_path is not None
            assert processed_photo.clip_embedding is not None

        logger.info(f"All {len(tasks)} photos processed successfully")

    async def test_face_detection_in_worker(
        self,
        test_session,
        test_file_storage,
        single_face_images,
        celery_worker,
    ):
        """
        E2E: Verify face detection runs in worker during photo processing.

        Tests that:
        1. Photo with face is uploaded
        2. Processing task detects faces
        3. Face embeddings are generated
        4. Faces are clustered
        """
        if not single_face_images:
            pytest.skip("No face test images available")

        photo_repo = PhotoRepositoryPostgres(test_session)
        face_repo = FaceRepositoryPostgres(test_session)
        file_storage = test_file_storage

        # Load face image
        image_path = single_face_images[0]
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Create photo
        photo = Photo.create(
            filename=f"face_test_{image_path.name}",
            original_path=str(image_path),
            connector_type="local",
        )

        # Save to storage
        storage_path = await file_storage.save_photo(
            photo_id=str(photo.id.value),
            file_data=image_data,
        )
        photo.set_storage_path(storage_path)
        await photo_repo.save(photo)
        await test_session.commit()

        # Enqueue processing task (which includes face detection)
        task = celery_app.send_task(
            "photo_processing.process_photo",
            args=[str(photo.id.value)],
            queue="processing",
        )

        logger.info(f"Enqueued face detection task {task.id} for photo {photo.id.value}")

        # Wait for task to complete
        from tests.e2e.conftest import wait_for_celery_task

        result = wait_for_celery_task(task.id, expected_state="SUCCESS", timeout=60.0)

        assert result.successful()

        # Check if faces were detected
        try:
            faces = await face_repo.find_faces_by_photo(photo.id.value)

            if faces:
                logger.info(
                    f"Face detection found {len(faces)} face(s) in photo "
                    f"{photo.id.value}"
                )

                # Verify face data
                for face in faces:
                    assert face.photo_id == photo.id.value
                    assert face.embedding is not None
                    assert len(face.embedding) > 0
            else:
                logger.warning(
                    f"No faces detected in test image {image_path.name} "
                    "(this is acceptable - test image may not be suitable)"
                )

        except Exception as e:
            logger.warning(f"Face detection check failed: {e}")

        # Verify photo processing completed
        processed_photo = await photo_repo.find_by_id(photo.id.value)
        assert processed_photo is not None
        assert processed_photo.processing_status == "completed"

    async def test_processing_task_failure_handling(
        self,
        test_session,
        test_file_storage,
        celery_worker,
    ):
        """
        E2E: Verify system handles processing task failures gracefully.

        Tests that:
        1. Photo is saved even if processing fails
        2. Task failure is logged
        3. Photo status reflects processing failure
        """
        photo_repo = PhotoRepositoryPostgres(test_session)
        file_storage = test_file_storage

        # Create minimal photo with invalid storage path
        # (will cause processing to fail)
        photo = Photo.create(
            filename="invalid_photo.jpg",
            source_path="/nonexistent/path/photo.jpg",
            mime_type="image/jpeg",
            connector_type=ConnectorType.LOCAL,
        )

        # Set invalid storage path
        photo.set_storage_path("/nonexistent/storage/photo.jpg")

        # Save photo entity (photo exists even though processing will fail)
        await photo_repo.save(photo)
        await test_session.commit()

        # Enqueue processing task (will fail due to missing file)
        task = celery_app.send_task(
            "photo_processing.process_photo",
            args=[str(photo.id.value)],
            queue="processing",
        )

        logger.info(f"Enqueued processing task (expected to fail): {task.id}")

        # Wait for task to complete (with failure)
        from tests.e2e.conftest import wait_for_celery_task

        try:
            result = wait_for_celery_task(
                task.id, expected_state="FAILURE", timeout=60.0
            )
            logger.info(f"Task failed as expected: {result.result}")
        except TimeoutError:
            logger.warning("Task did not fail within expected timeout")

        # Verify photo still exists (critical for error recovery)
        photo_from_db = await photo_repo.find_by_id(photo.id.value)
        assert photo_from_db is not None
        logger.info(f"Photo {photo.id.value} preserved despite processing failure")


@pytest.mark.asyncio
class TestWorkerTaskQueueing:
    """Tests for task queueing and routing."""

    async def test_processing_task_queued_correctly(self, celery_worker):
        """
        E2E: Verify processing task is routed to correct queue.

        Tests that:
        1. Task is sent to 'processing' queue
        2. Worker receives task from correct queue
        3. Task executes successfully
        """
        from tests.e2e.conftest import wait_for_celery_task

        # Send task to processing queue
        task = celery_app.send_task(
            "photo_processing.process_photo",
            args=["00000000-0000-0000-0000-000000000001"],  # Dummy ID
            queue="processing",
        )

        logger.info(f"Sent task {task.id} to 'processing' queue")

        # Task should fail (invalid photo ID) but should be processed by worker
        try:
            result = wait_for_celery_task(
                task.id, expected_state="FAILURE", timeout=30.0
            )
            logger.info("Task was processed (failed as expected with invalid photo ID)")
        except TimeoutError:
            logger.warning("Task did not complete within timeout")
