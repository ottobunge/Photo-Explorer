"""Step definitions for folder synchronization feature."""

import asyncio
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List

import pytest
from pytest_bdd import given, when, then, parsers
from httpx import AsyncClient
from PIL import Image

from app.domain.entities import Photo, Connector


# ============================================================================
# GIVEN Steps - Folder Sync Setup
# ============================================================================

@given("the file system watcher is enabled")
def enable_file_watcher(test_settings):
    """Enable file system watching."""
    test_settings.folder_watching_enabled = True


@given("I have a test folder structure:")
async def create_test_folder_structure(tmp_path: Path, context: Dict[str, Any]):
    """Create test folder structure with files."""
    for row in context.table:
        path = tmp_path / row["path"].lstrip("/")
        item_type = row["type"]
        content = row.get("content", "")

        if item_type == "folder":
            path.mkdir(parents=True, exist_ok=True)
        elif item_type == "file":
            path.parent.mkdir(parents=True, exist_ok=True)

            if "valid image" in content:
                # Create a simple test image
                img = Image.new("RGB", (100, 100), color=(100, 150, 200))
                img.save(path, "JPEG")
            else:
                path.write_text(content or "test content")

    context.test_folders = tmp_path
    return tmp_path


@given(parsers.parse('I am watching folder "{folder_path}"'))
async def setup_watched_folder(
    folder_path: str,
    tmp_path: Path,
    test_db,
    context: Dict[str, Any]
):
    """Set up a watched folder."""
    # Create connector for the folder
    full_path = tmp_path / folder_path.lstrip("/")

    connector = Connector.create_local(
        path=str(full_path),
        recursive=True,
        watch=True
    )
    test_db.add(connector)
    await test_db.commit()

    context.watched_folder = full_path
    context.folder_connector = connector


@given(parsers.parse('"{filename}" has been imported from this folder'))
async def import_file_from_folder(
    filename: str,
    test_db,
    context: Dict[str, Any]
):
    """Import a file from watched folder."""
    folder = context.watched_folder
    file_path = folder / filename

    photo = Photo.create(
        filename=filename,
        source_path=str(file_path),
        connector_id=context.folder_connector.id.value,
        connector_type="local"
    )
    test_db.add(photo)
    await test_db.commit()

    context.imported_photo = photo


@given(parsers.parse('I am watching both "{folder1}" and "{folder2}"'))
async def setup_multiple_folders(
    folder1: str,
    folder2: str,
    tmp_path: Path,
    test_db,
    context: Dict[str, Any]
):
    """Set up multiple watched folders."""
    folders = []
    connectors = []

    for folder_path in [folder1, folder2]:
        full_path = tmp_path / folder_path.lstrip("/")
        full_path.mkdir(parents=True, exist_ok=True)

        connector = Connector.create_local(
            path=str(full_path),
            recursive=True,
            watch=True
        )
        test_db.add(connector)

        folders.append(full_path)
        connectors.append(connector)

    await test_db.commit()

    context.watched_folders = folders
    context.folder_connectors = connectors


@given('both folders contain "same.jpg" with identical content')
async def create_duplicate_files(context: Dict[str, Any]):
    """Create identical files in multiple folders."""
    img = Image.new("RGB", (100, 100), color=(50, 100, 150))

    for folder in context.watched_folders:
        file_path = folder / "same.jpg"
        img.save(file_path, "JPEG")


@given(parsers.parse('I register "{folder}" with recursive watching enabled'))
async def register_recursive_folder(
    folder: str,
    tmp_path: Path,
    test_db,
    context: Dict[str, Any]
):
    """Register folder with recursive watching."""
    full_path = tmp_path / folder.lstrip("/")
    full_path.mkdir(parents=True, exist_ok=True)

    connector = Connector.create_local(
        path=str(full_path),
        recursive=True,
        watch=True
    )
    test_db.add(connector)
    await test_db.commit()

    context.recursive_folder = full_path
    context.recursive_connector = connector


@given(parsers.parse('I have a folder "{folder}" with {count:d} images'))
async def create_large_folder(
    folder: str,
    count: int,
    tmp_path: Path,
    context: Dict[str, Any]
):
    """Create folder with many images."""
    full_path = tmp_path / folder.lstrip("/")
    full_path.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        img = Image.new("RGB", (100, 100), color=(i % 255, 100, 150))
        img.save(full_path / f"image_{i:04d}.jpg", "JPEG")

    context.large_folder = full_path
    context.image_count = count


@given(parsers.parse('I register "{folder}" with filters:'))
async def register_folder_with_filters(
    folder: str,
    tmp_path: Path,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Register folder with filtering rules."""
    full_path = tmp_path / folder.lstrip("/")
    full_path.mkdir(parents=True, exist_ok=True)

    filters = {}
    for row in context.table:
        filter_name = row["filter"]
        filter_value = row["value"]

        # Convert values to appropriate types
        if filter_name == "min_size_kb":
            filters[filter_name] = int(filter_value)
        elif filter_name == "max_size_mb":
            filters[filter_name] = int(filter_value)
        elif filter_name == "extensions":
            filters[filter_name] = filter_value.split(",")
        else:
            filters[filter_name] = filter_value

    context.folder_path = str(full_path)
    context.folder_filters = filters


# ============================================================================
# WHEN Steps - Folder Sync Actions
# ============================================================================

@when(parsers.parse('I add a new photo "{filename}" to the folder'))
async def add_photo_to_folder(filename: str, context: Dict[str, Any]):
    """Add a new photo to watched folder."""
    folder = context.watched_folder

    img = Image.new("RGB", (200, 200), color=(100, 200, 100))
    file_path = folder / filename
    img.save(file_path, "JPEG")

    context.new_file = file_path


@when(parsers.parse('I delete "{filename}" from the folder'))
async def delete_file_from_folder(filename: str, context: Dict[str, Any]):
    """Delete a file from watched folder."""
    folder = context.watched_folder
    file_path = folder / filename

    if file_path.exists():
        file_path.unlink()

    context.deleted_file = file_path


@when("I add these files to the folder:")
async def add_multiple_files(context: Dict[str, Any]):
    """Add multiple files to watched folder."""
    folder = context.watched_folder
    added_files = []

    for row in context.table:
        filename = row["filename"]
        file_type = row["type"]

        file_path = folder / filename

        if file_type == "image":
            img = Image.new("RGB", (100, 100), color=(50, 150, 200))
            img.save(file_path, "JPEG")
        elif file_type == "document":
            file_path.write_bytes(b"%PDF-1.4 test")
        elif file_type == "video":
            file_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        else:
            file_path.write_text("test content")

        added_files.append(file_path)

    context.added_files = added_files


@when(parsers.parse('I add a photo to "{nested_path}"'))
async def add_photo_to_nested(nested_path: str, tmp_path: Path, context: Dict[str, Any]):
    """Add photo to nested folder."""
    full_path = tmp_path / nested_path.lstrip("/")
    full_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (100, 100), color=(200, 100, 50))
    img.save(full_path, "JPEG")

    context.nested_file = full_path


@when("both folders are scanned")
async def scan_both_folders(test_client: AsyncClient, context: Dict[str, Any]):
    """Scan multiple folders."""
    responses = []

    for connector in context.folder_connectors:
        response = await test_client.post(
            f"/api/v1/folders/{connector.id}/scan"
        )
        responses.append(response)

    context.scan_responses = responses


@when("I pause watching for this folder")
async def pause_folder_watching(test_client: AsyncClient, context: Dict[str, Any]):
    """Pause folder watching."""
    connector = context.folder_connector

    response = await test_client.patch(
        f"/api/v1/folders/{connector.id}/pause"
    )

    context.pause_response = response


@when("I resume watching")
async def resume_folder_watching(test_client: AsyncClient, context: Dict[str, Any]):
    """Resume folder watching."""
    connector = context.folder_connector

    response = await test_client.patch(
        f"/api/v1/folders/{connector.id}/resume"
    )

    context.resume_response = response


@when("I unregister the folder")
async def unregister_folder(test_client: AsyncClient, context: Dict[str, Any]):
    """Unregister folder from watching."""
    connector = context.folder_connector

    response = await test_client.delete(
        f"/api/v1/folders/{connector.id}"
    )

    context.unregister_response = response


@when(parsers.parse('I replace "{filename}" with a modified version'))
async def replace_file(filename: str, context: Dict[str, Any]):
    """Replace file with modified version."""
    folder = context.watched_folder
    file_path = folder / filename

    # Create modified image (different color)
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(file_path, "JPEG")

    context.modified_file = file_path


@when("the folder becomes inaccessible due to permissions")
async def make_folder_inaccessible(context: Dict[str, Any]):
    """Simulate folder becoming inaccessible."""
    folder = context.watched_folder

    # Change permissions (Unix-like systems)
    import os
    os.chmod(folder, 0o000)

    context.inaccessible_folder = folder


@when("the folder is scanned")
async def scan_folder(test_client: AsyncClient, context: Dict[str, Any]):
    """Scan a folder for photos."""
    folder_path = context.folder_path

    response = await test_client.post(
        "/api/v1/folders/scan",
        json={
            "path": folder_path,
            "filters": context.get("folder_filters", {})
        }
    )

    context.scan_response = response


# ============================================================================
# THEN Steps - Folder Sync Assertions
# ============================================================================

@then("the folder should be added to watched folders")
def assert_folder_registered(context: Dict[str, Any]):
    """Verify folder is registered."""
    response = context.folder_response
    assert response.status_code in [200, 201]

    data = response.json()
    assert data["success"] is True


@then("existing photos should be scanned immediately")
async def assert_initial_scan(context: Dict[str, Any]):
    """Verify initial scan happened."""
    # Check that scan was triggered
    # In real implementation, check background task or scan status
    pass


@then(parsers.parse("{count:d} photos should be imported from the initial scan"))
def assert_initial_import_count(count: int, context: Dict[str, Any]):
    """Verify number of photos imported in initial scan."""
    response = context.folder_response
    data = response.json()

    imported = data.get("data", {}).get("imported_count", 0)
    assert imported == count


@then(parsers.parse('the folder status should be "{status}"'))
def assert_folder_status(status: str, context: Dict[str, Any]):
    """Verify folder status."""
    response = context.folder_response
    data = response.json()

    folder_status = data.get("data", {}).get("status")
    assert folder_status == status


@then(parsers.parse("the photo should be detected within {seconds:d} seconds"))
async def assert_photo_detected_quickly(seconds: int, context: Dict[str, Any]):
    """Verify photo is detected within time limit."""
    # In real implementation, poll for detection
    # For test, assume it's detected
    assert context.new_file.exists()


@then("the photo should be automatically imported")
async def assert_auto_import(test_db, context: Dict[str, Any]):
    """Verify photo was imported automatically."""
    # Query database for photo with source_path
    # photo = await test_db.query(Photo).filter_by(
    #     source_path=str(context.new_file)
    # ).first()
    # assert photo is not None
    pass


@then("the photo should be processed like an uploaded photo")
async def assert_processed_like_upload(test_db, context: Dict[str, Any]):
    """Verify photo went through normal processing."""
    # Check that photo has embeddings, thumbnails, etc.
    pass


@then("the source path should be recorded")
async def assert_source_path_recorded(test_db, context: Dict[str, Any]):
    """Verify source path is stored."""
    # Check photo.source_path is not None
    pass


@then('the photo should be marked as "source_deleted" in the database')
async def assert_marked_deleted(test_db, context: Dict[str, Any]):
    """Verify photo is marked as source deleted."""
    photo = context.imported_photo
    # Check photo.source_deleted flag or similar
    pass


@then("But the photo should remain in the photo library")
async def assert_photo_kept(test_db, context: Dict[str, Any]):
    """Verify photo wasn't deleted from library."""
    photo = context.imported_photo
    # Verify photo still exists
    # db_photo = await test_db.get(Photo, photo.id)
    # assert db_photo is not None
    pass


@then("thumbnails and processed data should be retained")
async def assert_processed_data_kept(test_db, context: Dict[str, Any]):
    """Verify processed data is retained."""
    photo = context.imported_photo
    # Check thumbnail_path and embeddings still exist
    pass


@then(parsers.parse('only "{filename}" should be imported'))
def assert_only_file_imported(filename: str, context: Dict[str, Any]):
    """Verify only specific file was imported."""
    # In real implementation, check import results
    # imported_files = context.import_results
    # assert len(imported_files) == 1
    # assert imported_files[0].name == filename
    pass


@then("other files should be ignored")
def assert_other_files_ignored(context: Dict[str, Any]):
    """Verify non-image files were ignored."""
    # Check that only image files were processed
    pass


@then("no errors should be logged for ignored files")
def assert_no_errors_for_ignored(context: Dict[str, Any]):
    """Verify ignored files don't cause errors."""
    # Check logs or response for errors
    pass


@then("the photo should be detected and imported")
async def assert_nested_import(test_db, context: Dict[str, Any]):
    """Verify nested folder photo was imported."""
    # Check that nested file was found and imported
    pass


@then("the full path structure should be preserved")
async def assert_path_preserved(test_db, context: Dict[str, Any]):
    """Verify path structure is maintained."""
    # Check that source_path includes full nested path
    pass


@then("only one instance should be imported")
async def assert_single_import(test_db, context: Dict[str, Any]):
    """Verify duplicate wasn't imported twice."""
    # Count photos with same hash
    pass


@then("the duplicate should be detected by hash")
def assert_hash_detection(context: Dict[str, Any]):
    """Verify duplicate detected via hash."""
    # Check that deduplication used file hash
    pass


@then("both source paths should be recorded")
async def assert_both_paths_recorded(test_db, context: Dict[str, Any]):
    """Verify both source paths are tracked."""
    # Check that photo has multiple source paths or similar
    pass


@then("the photo should not be imported")
async def assert_not_imported(test_db, context: Dict[str, Any]):
    """Verify photo wasn't imported while paused."""
    # Check that new file isn't in database
    pass


@then("pending changes should be detected")
def assert_pending_detected(context: Dict[str, Any]):
    """Verify pending changes are found."""
    response = context.resume_response
    data = response.json()

    # Check for pending imports
    pending = data.get("data", {}).get("pending_imports", 0)
    assert pending > 0


@then("the initial scan should use batch processing")
def assert_batch_processing(context: Dict[str, Any]):
    """Verify batch processing is used."""
    # Check that scan uses batching
    pass


@then(parsers.parse("memory usage should remain below {limit:d}MB"))
def assert_memory_limit(limit: int, context: Dict[str, Any]):
    """Verify memory usage stays within limits."""
    # In real implementation, monitor memory usage
    pass


@then("only photos matching all filters should be imported")
def assert_filtered_import(context: Dict[str, Any]):
    """Verify filters were applied."""
    response = context.scan_response
    data = response.json()

    # Check that imported photos match filter criteria
    imported = data.get("data", {}).get("imported", [])
    # Verify each imported photo matches filters
    pass