"""
E2E test for photo upload flow.

Tests the complete workflow from upload to file retrieval:
1. Upload a photo via API
2. Verify photo is stored with correct paths
3. Verify photo file can be retrieved
4. Verify thumbnail generation (when worker processes)
5. Verify face detection (when worker processes)
"""

import io
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient
from PIL import Image

from app.adapters.outbound.storage import LocalFileStorage


@pytest.mark.asyncio
class TestPhotoUploadFlow:
    """E2E tests for complete photo upload workflow."""

    @pytest.fixture
    def sample_image_bytes(self) -> bytes:
        """Create a sample JPEG image for testing."""
        # Create a 200x200 red square
        img = Image.new("RGB", (200, 200), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    @pytest.fixture
    def sample_image_with_face(self) -> bytes:
        """Load a real test image with faces from test fixtures."""
        # Use the hopper.jpg test image (has a person's face)
        test_image_path = Path(__file__).parent.parent / "fixtures" / "hopper.jpg"

        if test_image_path.exists():
            return test_image_path.read_bytes()

        # Fallback: create a simple test image
        img = Image.new("RGB", (128, 128), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    async def test_upload_photo_creates_storage_file(
        self, client: AsyncClient, sample_image_bytes: bytes
    ):
        """
        E2E: Upload photo and verify file is stored correctly.

        This test verifies:
        - Photo uploaded successfully
        - storage_path is set
        - File exists on disk
        - File can be retrieved via API
        """
        # Step 1: Upload photo
        response = await client.post(
            "/photos/upload",
            files={"files": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["uploaded"]) == 1
        assert len(data["data"]["failed"]) == 0

        photo_id = data["data"]["uploaded"][0]["id"]

        # Step 2: Get photo metadata
        response = await client.get(f"/photos/{photo_id}")
        assert response.status_code == 200

        photo_data = response.json()["data"]
        assert photo_data["storage_path"] is not None
        assert photo_data["filename"] == "test.jpg"

        # Step 3: Verify file exists on disk
        file_storage = LocalFileStorage()
        storage_path = photo_data["storage_path"]
        file_data = await file_storage.get_file(storage_path)

        assert file_data is not None
        assert len(file_data) > 0
        assert file_data == sample_image_bytes

        # Step 4: Retrieve file via API
        response = await client.get(f"/photos/{photo_id}/file")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == sample_image_bytes

    async def test_upload_multiple_photos(
        self, client: AsyncClient, sample_image_bytes: bytes
    ):
        """
        E2E: Upload multiple photos in one request.

        Verifies batch upload and that all files are stored correctly.
        """
        # Upload 3 photos
        files = [
            ("files", (f"test{i}.jpg", sample_image_bytes, "image/jpeg"))
            for i in range(3)
        ]

        response = await client.post("/photos/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["uploaded"]) == 3
        assert len(data["data"]["failed"]) == 0

        # Verify each photo has storage_path and file is accessible
        file_storage = LocalFileStorage()

        for uploaded in data["data"]["uploaded"]:
            photo_id = uploaded["id"]

            # Get metadata
            response = await client.get(f"/photos/{photo_id}")
            photo_data = response.json()["data"]

            assert photo_data["storage_path"] is not None

            # Verify file exists
            file_data = await file_storage.get_file(photo_data["storage_path"])
            assert file_data is not None

    async def test_upload_photo_processing_workflow(
        self, client: AsyncClient, sample_image_bytes: bytes
    ):
        """
        E2E: Upload photo and verify processing status.

        Note: This test doesn't run the worker, so processing_status
        will remain "pending" or "processing". When worker is enabled,
        status should eventually become "completed".
        """
        # Upload photo
        response = await client.post(
            "/photos/upload",
            files={"files": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )

        photo_id = response.json()["data"]["uploaded"][0]["id"]

        # Get initial status
        response = await client.get(f"/photos/{photo_id}")
        photo_data = response.json()["data"]

        # Without worker, status should be pending or processing
        assert photo_data["processing_status"] in ["pending", "processing"]

        # Storage path should be set immediately
        assert photo_data["storage_path"] is not None

        # TODO: When worker is enabled in tests:
        # - Wait for processing to complete
        # - Verify thumbnail_path is set
        # - Verify thumbnail can be retrieved
        # - Verify CLIP embedding is stored

    async def test_upload_rejects_non_image_file(self, client: AsyncClient):
        """
        E2E: Verify that non-image files are rejected.
        """
        # Try to upload a text file
        text_content = b"This is not an image"

        response = await client.post(
            "/photos/upload",
            files={"files": ("test.txt", text_content, "text/plain")},
        )

        assert response.status_code == 201  # Request succeeds but file is rejected
        data = response.json()

        assert len(data["data"]["uploaded"]) == 0
        assert len(data["data"]["failed"]) == 1
        assert "Invalid file type" in data["data"]["failed"][0]["error"]

    async def test_upload_rejects_empty_file(self, client: AsyncClient):
        """
        E2E: Verify that empty files are rejected.
        """
        response = await client.post(
            "/photos/upload",
            files={"files": ("empty.jpg", b"", "image/jpeg")},
        )

        assert response.status_code == 201
        data = response.json()

        assert len(data["data"]["uploaded"]) == 0
        assert len(data["data"]["failed"]) == 1
        assert "Empty file" in data["data"]["failed"][0]["error"]

    async def test_upload_and_delete_photo(
        self, client: AsyncClient, sample_image_bytes: bytes
    ):
        """
        E2E: Upload photo, then delete it and verify cleanup.

        Verifies:
        - Photo is uploaded
        - File exists on disk
        - Photo can be deleted
        - File is removed from disk
        - Photo cannot be retrieved after deletion
        """
        # Step 1: Upload
        response = await client.post(
            "/photos/upload",
            files={"files": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )

        photo_id = response.json()["data"]["uploaded"][0]["id"]

        # Step 2: Verify file exists
        response = await client.get(f"/photos/{photo_id}")
        storage_path = response.json()["data"]["storage_path"]

        file_storage = LocalFileStorage()
        assert await file_storage.get_file(storage_path) is not None

        # Step 3: Delete photo
        response = await client.delete(f"/photos/{photo_id}")
        assert response.status_code == 200

        # Step 4: Verify file is removed
        assert await file_storage.get_file(storage_path) is None

        # Step 5: Verify photo cannot be retrieved
        response = await client.get(f"/photos/{photo_id}")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Requires worker to be running")
    async def test_upload_triggers_thumbnail_generation(
        self, client: AsyncClient, sample_image_bytes: bytes
    ):
        """
        E2E: Upload photo and verify thumbnail is generated.

        This test requires Celery worker to be running.
        Skipped by default - enable when worker is available in test env.
        """
        import asyncio

        # Upload photo
        response = await client.post(
            "/photos/upload",
            files={"files": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )

        photo_id = response.json()["data"]["uploaded"][0]["id"]

        # Wait for processing (max 10 seconds)
        for _ in range(20):
            await asyncio.sleep(0.5)

            response = await client.get(f"/photos/{photo_id}")
            photo_data = response.json()["data"]

            if photo_data["processing_status"] == "completed":
                break

        # Verify thumbnail was generated
        assert photo_data["thumbnail_path"] is not None

        # Verify thumbnail can be retrieved
        response = await client.get(f"/photos/{photo_id}/thumbnail")
        assert response.status_code == 200
        assert response.headers["content-type"] in ["image/jpeg", "image/png", "image/webp"]

        # Verify thumbnail is smaller than original
        thumbnail_size = len(response.content)
        original_size = len(sample_image_bytes)
        assert thumbnail_size < original_size

    @pytest.mark.skip(reason="Requires worker to be running")
    async def test_upload_triggers_face_detection(
        self, client: AsyncClient, sample_image_with_face: bytes
    ):
        """
        E2E: Upload photo with faces and verify face detection runs.

        This test requires Celery worker to be running.
        Skipped by default - enable when worker is available in test env.
        """
        import asyncio

        # Upload photo
        response = await client.post(
            "/photos/upload",
            files={"files": ("person.jpg", sample_image_with_face, "image/jpeg")},
        )

        photo_id = response.json()["data"]["uploaded"][0]["id"]

        # Wait for face detection (max 15 seconds)
        for _ in range(30):
            await asyncio.sleep(0.5)

            # Check if faces were detected
            response = await client.get(f"/faces/clusters?photo_id={photo_id}")
            if response.status_code == 200:
                faces_data = response.json()
                if faces_data.get("data", {}).get("clusters"):
                    break

        # Verify faces were detected
        assert len(faces_data["data"]["clusters"]) > 0


@pytest.mark.asyncio
class TestPhotoFileRetrieval:
    """E2E tests for photo file retrieval."""

    async def test_get_nonexistent_photo_file_returns_404(self, client: AsyncClient):
        """Verify that requesting a non-existent photo returns 404."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"

        response = await client.get(f"/photos/{fake_uuid}/file")
        assert response.status_code == 404

    async def test_get_nonexistent_thumbnail_returns_404(self, client: AsyncClient):
        """Verify that requesting a non-existent thumbnail returns 404."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"

        response = await client.get(f"/photos/{fake_uuid}/thumbnail")
        assert response.status_code == 404
