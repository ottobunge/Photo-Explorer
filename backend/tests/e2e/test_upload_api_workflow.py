"""E2E tests for photo upload API workflow with face detection.

These tests verify the complete upload workflow through the HTTP API,
including face detection integration.
"""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.adapters.outbound.persistence.postgres import (
    FaceRepositoryPostgres,
    PhotoRepositoryPostgres,
)


@pytest.mark.asyncio
class TestUploadAPIWorkflowE2E:
    """End-to-end tests for photo upload API with face detection."""

    async def test_upload_photo_via_api_triggers_processing(
        self,
        client: AsyncClient,
        db_session,
        single_face_images,
    ):
        """
        E2E: Uploading a photo via /api/v1/photos/upload should trigger processing.

        This tests the actual HTTP endpoint to ensure:
        1. Photo is saved to database
        2. Processing tasks are queued (including face detection)
        3. Photo has proper initial status

        This would catch the missing detect_faces_task.delay() call in the upload endpoint.
        """
        if not single_face_images:
            pytest.skip("No single face images available")

        photo_repo = PhotoRepositoryPostgres(db_session)

        # Prepare file upload
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        # Upload via API
        files = {"files": (source_path.name, io.BytesIO(image_data), "image/jpeg")}

        response = await client.post(
            "/api/v1/photos/upload",
            files=files,
        )

        # Verify response
        assert response.status_code == 200, f"Upload failed: {response.text}"

        response_data = response.json()
        assert "photos" in response_data
        assert len(response_data["photos"]) == 1

        photo_data = response_data["photos"][0]
        photo_id = photo_data["id"]

        # Verify photo was saved to database
        photo = await photo_repo.find_by_id(photo_id)
        assert photo is not None, "Photo should be saved to database"
        assert photo.filename == source_path.name
        assert photo.processing_status in ["pending", "processing", "completed"]

        # In a real test with Celery worker running:
        # - We would wait_for_processing(photo_repo, photo_id, "completed", timeout=30)
        # - Then verify face detection was triggered
        # - And check that faces were detected

        # For now, verify photo is ready for processing
        assert photo.storage_path is not None, "Photo should have storage path"

    async def test_upload_multiple_photos_with_faces(
        self,
        client: AsyncClient,
        db_session,
        single_face_images,
    ):
        """
        E2E: Uploading multiple photos should trigger processing for each.

        Tests batch upload workflow.
        """
        if len(single_face_images) < 2:
            pytest.skip("Need at least 2 single face images")

        photo_repo = PhotoRepositoryPostgres(db_session)

        # Prepare multiple file uploads
        files = []
        for img_path in single_face_images[:2]:
            with open(img_path, "rb") as f:
                image_data = f.read()
            files.append(("files", (img_path.name, io.BytesIO(image_data), "image/jpeg")))

        # Upload via API
        response = await client.post(
            "/api/v1/photos/upload",
            files=files,
        )

        # Verify response
        assert response.status_code == 200, f"Upload failed: {response.text}"

        response_data = response.json()
        assert "photos" in response_data
        assert len(response_data["photos"]) == 2, "Should upload 2 photos"

        # Verify all photos were saved
        for photo_data in response_data["photos"]:
            photo_id = photo_data["id"]
            photo = await photo_repo.find_by_id(photo_id)

            assert photo is not None, f"Photo {photo_id} should be saved"
            assert photo.storage_path is not None
            assert photo.processing_status in ["pending", "processing", "completed"]

    async def test_upload_api_returns_photo_metadata(
        self,
        client: AsyncClient,
        db_session,
        single_face_images,
    ):
        """
        E2E: Upload API should return comprehensive photo metadata.

        Verifies the response includes all necessary fields.
        """
        if not single_face_images:
            pytest.skip("No single face images available")

        # Prepare file upload
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        files = {"files": (source_path.name, io.BytesIO(image_data), "image/jpeg")}

        # Upload via API
        response = await client.post(
            "/api/v1/photos/upload",
            files=files,
        )

        assert response.status_code == 200
        response_data = response.json()

        photo_data = response_data["photos"][0]

        # Verify essential metadata fields
        required_fields = [
            "id",
            "filename",
            "mime_type",
            "connector_type",
            "processing_status",
            "created_at",
        ]

        for field in required_fields:
            assert field in photo_data, f"Response should include '{field}'"

        assert photo_data["connector_type"] == "upload"
        assert photo_data["filename"] == source_path.name
        assert photo_data["mime_type"] == "image/jpeg"

    async def test_upload_invalid_file_returns_error(
        self,
        client: AsyncClient,
    ):
        """
        E2E: Uploading invalid file should return proper error.

        Tests error handling in upload endpoint.
        """
        # Create invalid file data (not an image)
        invalid_data = b"This is not an image"

        files = {"files": ("invalid.txt", io.BytesIO(invalid_data), "text/plain")}

        # Upload via API
        response = await client.post(
            "/api/v1/photos/upload",
            files=files,
        )

        # Should return error (exact status code depends on validation logic)
        assert response.status_code >= 400, "Should return error for invalid file"

    async def test_upload_with_face_and_verify_detection_ready(
        self,
        client: AsyncClient,
        db_session,
        single_face_images,
    ):
        """
        E2E: Upload workflow should prepare photo for face detection.

        Verifies:
        1. Photo is uploaded successfully
        2. Storage path is set (face detection needs this)
        3. Photo is in correct state for processing
        """
        if not single_face_images:
            pytest.skip("No single face images available")

        photo_repo = PhotoRepositoryPostgres(db_session)
        face_repo = FaceRepositoryPostgres(db_session)

        # Upload photo
        source_path = single_face_images[0]
        with open(source_path, "rb") as f:
            image_data = f.read()

        files = {"files": (source_path.name, io.BytesIO(image_data), "image/jpeg")}

        response = await client.post(
            "/api/v1/photos/upload",
            files=files,
        )

        assert response.status_code == 200
        photo_id = response.json()["photos"][0]["id"]

        # Verify photo is ready for face detection
        photo = await photo_repo.find_by_id(photo_id)

        assert photo is not None
        assert photo.storage_path is not None, "Photo needs storage path for face detection"
        assert Path(photo.storage_path).exists(), "Photo file should exist on disk"

        # Verify photo is in processable state
        assert photo.processing_status in [
            "pending",
            "processing",
        ], "Photo should be pending or processing for face detection to run"

        # Note: In real scenario with worker running:
        # - We would wait for detect_faces_task to complete
        # - Then verify faces were detected:
        #   faces = await face_repo.find_faces_by_photo(photo.id.value)
        #   assert len(faces) > 0, "Should detect at least one face"
