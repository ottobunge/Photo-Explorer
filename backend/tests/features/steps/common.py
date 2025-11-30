"""Common step definitions shared across all features."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from pytest_bdd import given, when, then, parsers
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Photo, Album, FaceCluster
from app.main import app


# ============================================================================
# GIVEN Steps - Setup and Preconditions
# ============================================================================

@given("the system is ready to accept uploads")
def system_ready(test_client: AsyncClient):
    """Ensure the system is initialized and ready."""
    response = asyncio.run(test_client.get("/api/v1/health"))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@given("ML services are available")
def ml_services_ready(test_client: AsyncClient):
    """Check that ML services are initialized."""
    response = asyncio.run(test_client.get("/api/v1/health"))
    assert response.status_code == 200
    data = response.json()
    assert data.get("ml_status") in ["ready", "healthy"]


@given("the vector database is initialized")
def vector_db_ready(test_client: AsyncClient):
    """Ensure vector database is ready."""
    response = asyncio.run(test_client.get("/api/v1/health"))
    assert response.status_code == 200
    data = response.json()
    assert data.get("vector_db") in ["ready", "healthy"]


@given("face detection service is enabled")
def face_detection_enabled(test_settings):
    """Ensure face detection is enabled in settings."""
    test_settings.face_detection_enabled = True
    assert test_settings.face_detection_enabled is True


@given("I am authenticated as a user")
def authenticated_user(test_client: AsyncClient, auth_headers):
    """Set up authentication for the test user."""
    # In a real implementation, this would set up auth tokens
    # For now, we'll use a test auth header
    test_client.headers.update(auth_headers)


@given(parsers.parse('I have a valid image file "{filename}"'))
def prepare_valid_image(filename: str, test_fixtures_dir: Path):
    """Prepare a valid test image file."""
    file_path = test_fixtures_dir / "images" / filename
    if not file_path.exists():
        # Create a minimal valid JPEG for testing
        create_test_image(file_path, filename)
    assert file_path.exists()
    return file_path


@given(parsers.parse('I have a non-image file "{filename}"'))
def prepare_non_image_file(filename: str, test_fixtures_dir: Path):
    """Prepare a non-image test file."""
    file_path = test_fixtures_dir / "files" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if filename.endswith(".pdf"):
        file_path.write_bytes(b"%PDF-1.4 test content")
    elif filename.endswith(".txt"):
        file_path.write_text("Test text file")
    else:
        file_path.write_bytes(b"Generic file content")

    assert file_path.exists()
    return file_path


@given(parsers.parse('I have already uploaded "{filename}" with hash "{file_hash}"'))
async def photo_already_uploaded(
    filename: str,
    file_hash: str,
    test_db: AsyncSession,
    test_fixtures_dir: Path
):
    """Create a photo record in the database."""
    photo = Photo.create(
        filename=filename,
        storage_path=f"test/{filename}",
        file_hash=file_hash,
    )
    test_db.add(photo)
    await test_db.commit()
    return photo


@given("I have photos in my library:")
def setup_photo_library(test_db: AsyncSession, context: Dict[str, Any]):
    """Set up photos in the test database."""
    photos = []
    for row in context.table:
        photo = Photo.create(
            id=row["photo_id"],
            filename=row["filename"],
            taken_at=row.get("date_taken"),
        )
        photos.append(photo)
        test_db.add(photo)

    asyncio.run(test_db.commit())
    context.photos = photos
    return photos


@given(parsers.parse('I have an album "{album_name}"'))
async def create_album(album_name: str, test_db: AsyncSession):
    """Create an album in the database."""
    album = Album.create(name=album_name)
    test_db.add(album)
    await test_db.commit()
    return album


# ============================================================================
# WHEN Steps - Actions
# ============================================================================

@when("I upload the photo")
async def upload_single_photo(test_client: AsyncClient, context: Dict[str, Any]):
    """Upload a single photo via the API."""
    file_path = context.get("file_path")

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/jpeg")}
        response = await test_client.post(
            "/api/v1/photos/upload",
            files=files
        )

    context.upload_response = response
    return response


@when(parsers.parse('I search for "{query}"'))
async def search_photos(query: str, test_client: AsyncClient, context: Dict[str, Any]):
    """Perform a semantic search."""
    response = await test_client.get(
        "/api/v1/search",
        params={"q": query}
    )
    context.search_response = response
    context.search_results = response.json().get("data", {}).get("results", [])
    return response


@when(parsers.parse('I create an album named "{album_name}"'))
async def create_new_album(album_name: str, test_client: AsyncClient, context: Dict[str, Any]):
    """Create a new album via API."""
    response = await test_client.post(
        "/api/v1/albums",
        json={"name": album_name}
    )
    context.album_response = response
    return response


@when(parsers.parse('I register "{folder_path}" for watching'))
async def register_folder(folder_path: str, test_client: AsyncClient, context: Dict[str, Any]):
    """Register a folder for watching."""
    response = await test_client.post(
        "/api/v1/folders/register",
        json={
            "path": folder_path,
            "recursive": True,
            "watch": True,
        }
    )
    context.folder_response = response
    return response


# ============================================================================
# THEN Steps - Assertions
# ============================================================================

@then("the upload should be successful")
def assert_upload_success(context: Dict[str, Any]):
    """Assert that upload was successful."""
    response = context.upload_response
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True


@then("the photo should be stored in the database")
async def assert_photo_in_database(context: Dict[str, Any], test_db: AsyncSession):
    """Verify photo exists in database."""
    response_data = context.upload_response.json()
    photo_id = response_data["data"]["id"]

    photo = await test_db.get(Photo, photo_id)
    assert photo is not None


@then(parsers.parse('the upload should be rejected with status {status:d}'))
def assert_upload_rejected(status: int, context: Dict[str, Any]):
    """Assert upload was rejected with specific status."""
    response = context.upload_response
    assert response.status_code == status


@then(parsers.parse('the error message should contain "{expected_text}"'))
def assert_error_message_contains(expected_text: str, context: Dict[str, Any]):
    """Check error message contains expected text."""
    response = context.upload_response or context.album_response
    data = response.json()
    error_message = data.get("error", {}).get("message", "")
    assert expected_text.lower() in error_message.lower()


@then("results should be ranked by semantic similarity")
def assert_semantic_ranking(context: Dict[str, Any]):
    """Verify results are ordered by similarity score."""
    results = context.search_results
    scores = [r.get("similarity_score", 0) for r in results]
    assert scores == sorted(scores, reverse=True)


@then("the album should be created successfully")
def assert_album_created(context: Dict[str, Any]):
    """Verify album was created."""
    response = context.album_response
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "id" in data["data"]


@then("the folder should be added to watched folders")
def assert_folder_registered(context: Dict[str, Any]):
    """Verify folder was registered for watching."""
    response = context.folder_response
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["success"] is True


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_image(file_path: Path, filename: str):
    """Create a minimal valid JPEG file for testing."""
    from PIL import Image

    # Create a simple 100x100 image
    img = Image.new("RGB", (100, 100), color="red")

    # Add some variation based on filename
    if "sunset" in filename:
        img = Image.new("RGB", (100, 100), color=(255, 100, 0))
    elif "beach" in filename:
        img = Image.new("RGB", (100, 100), color=(0, 150, 255))
    elif "family" in filename:
        # Add simple shapes to simulate faces
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.ellipse([20, 20, 40, 40], fill=(255, 200, 150))
        draw.ellipse([60, 20, 80, 40], fill=(255, 200, 150))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(file_path, "JPEG")


def create_test_fixtures_dir(tmp_path: Path) -> Path:
    """Create test fixtures directory structure."""
    fixtures_dir = tmp_path / "fixtures"
    (fixtures_dir / "images").mkdir(parents=True, exist_ok=True)
    (fixtures_dir / "files").mkdir(parents=True, exist_ok=True)
    return fixtures_dir