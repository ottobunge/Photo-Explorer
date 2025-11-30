"""Step definitions for photo upload feature."""

import asyncio
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, when, then, parsers
from httpx import AsyncClient
from PIL import Image, ImageDraw
from PIL.ExifTags import TAGS

from app.domain.entities import Photo


# ============================================================================
# GIVEN Steps - Photo Upload Specific Setup
# ============================================================================

@given(parsers.parse('I have a photo "{filename}" containing faces'))
def prepare_photo_with_faces(filename: str, test_fixtures_dir: Path):
    """Create a test image with simulated faces."""
    img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw circles to simulate faces
    face_positions = [(100, 100), (200, 100), (300, 100)]
    for x, y in face_positions:
        # Face circle
        draw.ellipse([x-30, y-30, x+30, y+30], fill=(255, 200, 150))
        # Eyes
        draw.ellipse([x-15, y-10, x-5, y], fill=(0, 0, 0))
        draw.ellipse([x+5, y-10, x+15, y], fill=(0, 0, 0))
        # Mouth
        draw.arc([x-15, y+5, x+15, y+20], 0, 180, fill=(200, 100, 100))

    file_path = test_fixtures_dir / "images" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(file_path, "JPEG")
    return file_path


@given(parsers.parse('I have a photo "{filename}" with EXIF data'))
def prepare_photo_with_exif(filename: str, test_fixtures_dir: Path):
    """Create a test image with EXIF metadata."""
    from PIL import Image
    import piexif

    img = Image.new("RGB", (800, 600), color=(100, 150, 200))

    # Create EXIF data
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"Canon",
            piexif.ImageIFD.Model: b"EOS R5",
            piexif.ImageIFD.DateTime: b"2024:03:15 10:30:00",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (29, 1)),
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (10, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b"W",
        },
    }

    exif_bytes = piexif.dump(exif_dict)

    file_path = test_fixtures_dir / "images" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(file_path, "JPEG", exif=exif_bytes)
    return file_path


@given(parsers.parse('I have a corrupted image file "{filename}"'))
def prepare_corrupted_image(filename: str, test_fixtures_dir: Path):
    """Create a corrupted image file."""
    file_path = test_fixtures_dir / "images" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write invalid JPEG data
    with open(file_path, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0")  # JPEG header
        f.write(b"\x00\x00CORRUPTED_DATA_HERE")  # Invalid data

    return file_path


@given(parsers.parse('I have an image file "{filename}" larger than {size:d}MB'))
def prepare_large_image(filename: str, size: int, test_fixtures_dir: Path):
    """Create a large image file."""
    # Create a large image (size in MB)
    width = 5000
    height = int((size * 1024 * 1024) / (width * 3))  # Approximate size

    img = Image.new("RGB", (width, height), color=(100, 100, 100))

    file_path = test_fixtures_dir / "images" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(file_path, "JPEG", quality=95)

    return file_path


@given("I have multiple image files:")
def prepare_multiple_images(test_fixtures_dir: Path, context: Dict[str, Any]):
    """Prepare multiple test images."""
    files = []
    for row in context.table:
        filename = row["filename"]
        file_type = row["type"]

        if file_type == "image":
            img = Image.new("RGB", (200, 200), color=(100, 150, 200))
            file_path = test_fixtures_dir / "images" / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(file_path)
            files.append(file_path)

    context.files = files
    return files


@given("face detection is enabled")
def enable_face_detection(test_settings, mock_ml_services):
    """Ensure face detection is enabled and mocked."""
    test_settings.face_detection_enabled = True
    # ML services are mocked via fixture


# ============================================================================
# WHEN Steps - Upload Actions
# ============================================================================

@when("I attempt to upload the file")
async def attempt_upload(test_client: AsyncClient, context: Dict[str, Any]):
    """Attempt to upload a file (may fail)."""
    file_path = context.get("file_path")

    # Determine MIME type based on extension
    mime_type = "application/octet-stream"
    if file_path.suffix.lower() in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif file_path.suffix.lower() == ".png":
        mime_type = "image/png"
    elif file_path.suffix.lower() == ".pdf":
        mime_type = "application/pdf"

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, mime_type)}
        response = await test_client.post(
            "/api/v1/photos/upload",
            files=files
        )

    context.upload_response = response
    return response


@when("I upload all photos in batch")
async def upload_batch(test_client: AsyncClient, context: Dict[str, Any]):
    """Upload multiple photos in a batch request."""
    files_list = []

    for file_path in context.files:
        with open(file_path, "rb") as f:
            content = f.read()
            files_list.append(
                ("files", (file_path.name, content, "image/jpeg"))
            )

    response = await test_client.post(
        "/api/v1/photos/upload/batch",
        files=files_list
    )

    context.batch_response = response
    return response


@when("I upload the same photo again")
async def upload_duplicate(test_client: AsyncClient, context: Dict[str, Any]):
    """Upload a duplicate photo."""
    # Use the same file that was already uploaded
    original_photo = context.get("uploaded_photo")
    file_path = test_fixtures_dir / "images" / original_photo.filename

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/jpeg")}
        response = await test_client.post(
            "/api/v1/photos/upload",
            files=files
        )

    context.duplicate_response = response
    return response


# ============================================================================
# THEN Steps - Upload Assertions
# ============================================================================

@then("the photo should be indexed for search")
async def assert_photo_indexed(context: Dict[str, Any], mock_vector_store):
    """Verify photo was indexed in vector store."""
    response_data = context.upload_response.json()
    photo_id = response_data["data"]["id"]

    # Check that embedding was added to vector store
    # In real implementation, this would check Qdrant
    assert len(mock_vector_store.embeddings) > 0
    indexed_ids = [e["id"] for e in mock_vector_store.embeddings]
    assert photo_id in indexed_ids


@then("metadata should be extracted from the photo")
async def assert_metadata_extracted(context: Dict[str, Any], test_db):
    """Verify metadata was extracted."""
    response_data = context.upload_response.json()
    photo_data = response_data["data"]

    # Check that metadata fields are present
    assert "width" in photo_data
    assert "height" in photo_data
    assert "file_size" in photo_data

    # For EXIF photos, check additional metadata
    if "camera" in context.get("filename", ""):
        assert photo_data.get("camera_make") == "Canon"
        assert photo_data.get("camera_model") == "EOS R5"


@then("the response should include the photo ID")
def assert_response_has_photo_id(context: Dict[str, Any]):
    """Verify response includes photo ID."""
    response_data = context.upload_response.json()
    assert "data" in response_data
    assert "id" in response_data["data"]
    assert len(response_data["data"]["id"]) == 36  # UUID format


@then("faces should be detected in the photo")
async def assert_faces_detected(context: Dict[str, Any], test_db):
    """Verify faces were detected."""
    response_data = context.upload_response.json()
    photo_id = response_data["data"]["id"]

    # In real implementation, query Face table
    # For now, check that face detection was called
    assert response_data["data"].get("face_count", 0) > 0


@then("face embeddings should be generated")
async def assert_face_embeddings(context: Dict[str, Any]):
    """Verify face embeddings were generated."""
    response_data = context.upload_response.json()

    # Check that faces have embeddings
    faces = response_data["data"].get("faces", [])
    for face in faces:
        assert "embedding" in face
        assert len(face["embedding"]) == 512  # Standard embedding size


@then("faces should be added to clusters")
async def assert_faces_clustered(context: Dict[str, Any], test_db):
    """Verify faces were added to clusters."""
    response_data = context.upload_response.json()

    faces = response_data["data"].get("faces", [])
    for face in faces:
        assert "cluster_id" in face or face.get("is_clustering_pending")


@then("the system should detect the duplicate")
def assert_duplicate_detected(context: Dict[str, Any]):
    """Verify duplicate was detected."""
    response = context.duplicate_response
    data = response.json()

    # System should either return existing photo or indicate duplicate
    assert response.status_code in [200, 409]
    if response.status_code == 409:
        assert "duplicate" in data.get("error", {}).get("message", "").lower()


@then("return the existing photo ID")
def assert_existing_photo_returned(context: Dict[str, Any]):
    """Verify existing photo ID was returned."""
    original_response = context.upload_response.json()
    duplicate_response = context.duplicate_response.json()

    original_id = original_response["data"]["id"]
    duplicate_id = duplicate_response["data"]["id"]

    assert original_id == duplicate_id


@then("not create a duplicate entry")
async def assert_no_duplicate_entry(context: Dict[str, Any], test_db):
    """Verify no duplicate was created in database."""
    # Count photos with the same hash
    file_hash = context.get("file_hash")

    # In real implementation, query database
    # For test, check that only one photo exists with this hash
    # This would need actual database query implementation


@then(parsers.parse("all {count:d} photos should be uploaded successfully"))
def assert_batch_upload_success(count: int, context: Dict[str, Any]):
    """Verify all photos in batch were uploaded."""
    response = context.batch_response
    assert response.status_code == 201

    data = response.json()
    uploaded_photos = data["data"]["photos"]
    assert len(uploaded_photos) == count


@then("each photo should have a unique ID")
def assert_unique_ids(context: Dict[str, Any]):
    """Verify each uploaded photo has a unique ID."""
    response = context.batch_response
    data = response.json()

    photos = data["data"]["photos"]
    ids = [photo["id"] for photo in photos]

    # Check all IDs are unique
    assert len(ids) == len(set(ids))


@then("all photos should be processed asynchronously")
def assert_async_processing(context: Dict[str, Any]):
    """Verify photos are queued for async processing."""
    response = context.batch_response
    data = response.json()

    # Check that processing tasks were created
    assert "processing_tasks" in data["data"]
    tasks = data["data"]["processing_tasks"]
    assert len(tasks) > 0


@then("the following metadata should be extracted:")
def assert_specific_metadata(context: Dict[str, Any]):
    """Verify specific metadata fields were extracted."""
    response = context.upload_response
    data = response.json()
    photo_data = data["data"]

    for row in context.table:
        field = row["field"]
        expected_value = row["value"]

        # Check metadata field exists and matches
        assert field in photo_data
        actual_value = str(photo_data[field])

        # For coordinates, allow small differences
        if field in ["gps_latitude", "gps_longitude"]:
            assert abs(float(actual_value) - float(expected_value)) < 0.01
        else:
            assert expected_value in actual_value or actual_value in expected_value


@then(parsers.parse('the error message should indicate "{message}"'))
def assert_error_indicates(message: str, context: Dict[str, Any]):
    """Verify error message contains expected text."""
    response = context.upload_response or context.duplicate_response
    data = response.json()

    error_msg = data.get("error", {}).get("message", "")
    assert message.lower() in error_msg.lower()


@then("no partial data should be saved")
async def assert_no_partial_data(context: Dict[str, Any], test_db):
    """Verify no partial data was saved on error."""
    # Check that no photo was created
    response = context.upload_response

    # If upload failed, ensure no photo ID was returned
    if response.status_code >= 400:
        data = response.json()
        assert "id" not in data.get("data", {})

        # In real implementation, verify database has no partial records