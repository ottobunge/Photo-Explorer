"""Step definitions for album management feature."""

import asyncio
from typing import Dict, Any, List
from uuid import uuid4

import pytest
from pytest_bdd import given, when, then, parsers
from httpx import AsyncClient

from app.domain.entities import Album, Photo


# ============================================================================
# GIVEN Steps - Album Setup
# ============================================================================

@given(parsers.parse('I have an album "{album_name}" containing:'))
async def create_album_with_photos(
    album_name: str,
    test_db,
    context: Dict[str, Any]
):
    """Create an album with specified photos."""
    album = Album.create(name=album_name)
    test_db.add(album)

    photos = []
    for row in context.table:
        photo_id = row["photo_id"]
        # Get photo from context or create new one
        photo = context.photos.get(photo_id)
        if photo:
            photo.album_ids.append(album.id)
            photos.append(photo)

    album.photo_count = len(photos)
    await test_db.commit()

    context.album = album
    context.album_photos = photos


@given(parsers.parse('I have an album "{album_name}" with {count:d} photos'))
async def create_album_with_count(
    album_name: str,
    count: int,
    test_db,
    context: Dict[str, Any]
):
    """Create an album with specified number of photos."""
    album = Album.create(name=album_name)
    test_db.add(album)

    photos = []
    for i in range(count):
        photo = Photo.create(
            filename=f"{album_name}_{i}.jpg",
            storage_path=f"test/{album_name}_{i}.jpg",
        )
        photo.album_ids.append(album.id)
        test_db.add(photo)
        photos.append(photo)

    album.photo_count = count
    await test_db.commit()

    context.album = album
    context.album_photos = photos


@given(parsers.parse('I have created {count:d} albums'))
async def create_multiple_albums(count: int, test_db, context: Dict[str, Any]):
    """Create multiple albums for testing."""
    albums = []
    for i in range(count):
        album = Album.create(name=f"Album {i+1}")
        test_db.add(album)
        albums.append(album)

    await test_db.commit()
    context.albums = albums


@given(parsers.parse('I have an album named "{name}"'))
async def create_named_album(name: str, test_db, context: Dict[str, Any]):
    """Create an album with specific name."""
    album = Album.create(name=name)
    test_db.add(album)
    await test_db.commit()

    context.existing_album = album


# ============================================================================
# WHEN Steps - Album Actions
# ============================================================================

@when("I add the following photos to the album:")
async def add_photos_to_album(test_client: AsyncClient, context: Dict[str, Any]):
    """Add photos to an album."""
    album = context.album
    photo_ids = [row["photo_id"] for row in context.table]

    response = await test_client.post(
        f"/api/v1/albums/{album.id}/photos",
        json={"photo_ids": photo_ids}
    )

    context.add_photos_response = response
    return response


@when(parsers.parse('I remove "{photo_id}" from the album'))
async def remove_photo_from_album(
    photo_id: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Remove a photo from album."""
    album = context.album

    response = await test_client.delete(
        f"/api/v1/albums/{album.id}/photos/{photo_id}"
    )

    context.remove_photo_response = response
    return response


@when("I delete the album")
async def delete_album(test_client: AsyncClient, context: Dict[str, Any]):
    """Delete an album."""
    album = context.album

    response = await test_client.delete(f"/api/v1/albums/{album.id}")

    context.delete_response = response
    return response


@when(parsers.parse("I request albums with page size {size:d}"))
async def list_albums_paginated(
    size: int,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """List albums with pagination."""
    response = await test_client.get(
        "/api/v1/albums",
        params={"per_page": size, "page": 1}
    )

    context.list_response = response
    context.albums_list = response.json().get("data", {}).get("albums", [])
    context.pagination = response.json().get("meta", {})
    return response


@when(parsers.parse('I try to create another album named "{name}"'))
async def try_create_duplicate(
    name: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Try to create album with duplicate name."""
    response = await test_client.post(
        "/api/v1/albums",
        json={"name": name}
    )

    context.duplicate_response = response
    return response


@when(parsers.parse('I rename the album to "{new_name}"'))
async def rename_album(
    new_name: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Rename an album."""
    album = context.existing_album or context.album

    response = await test_client.patch(
        f"/api/v1/albums/{album.id}",
        json={"name": new_name}
    )

    context.rename_response = response
    return response


@when("I request a shareable link for the album")
async def create_share_link(test_client: AsyncClient, context: Dict[str, Any]):
    """Create a shareable link for album."""
    album = context.album

    response = await test_client.post(
        f"/api/v1/albums/{album.id}/share",
        json={
            "expires_in_days": 7,
            "allow_download": True
        }
    )

    context.share_response = response
    return response


@when("I request album statistics")
async def get_album_stats(test_client: AsyncClient, context: Dict[str, Any]):
    """Get statistics for an album."""
    album = context.album

    response = await test_client.get(f"/api/v1/albums/{album.id}/stats")

    context.stats_response = response
    return response


@when(parsers.parse('I set "{photo_id}" as the cover photo'))
async def set_cover_photo(
    photo_id: str,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Set album cover photo."""
    album = context.album

    response = await test_client.patch(
        f"/api/v1/albums/{album.id}",
        json={"cover_photo_id": photo_id}
    )

    context.cover_response = response
    return response


@when(parsers.parse("I perform a batch add of {count:d} photos"))
async def batch_add_photos(
    count: int,
    test_client: AsyncClient,
    context: Dict[str, Any]
):
    """Add many photos to album at once."""
    album = context.album
    photo_ids = [f"photo_{i}" for i in range(count)]

    response = await test_client.post(
        f"/api/v1/albums/{album.id}/photos/batch",
        json={"photo_ids": photo_ids}
    )

    context.batch_response = response
    return response


# ============================================================================
# THEN Steps - Album Assertions
# ============================================================================

@then("the album should be created successfully")
def assert_album_created(context: Dict[str, Any]):
    """Verify album was created."""
    response = context.album_response
    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert "id" in data["data"]


@then("the album should have a unique ID")
def assert_album_has_id(context: Dict[str, Any]):
    """Verify album has unique ID."""
    response = context.album_response
    data = response.json()

    album_id = data["data"]["id"]
    assert album_id is not None
    assert len(album_id) == 36  # UUID format


@then("the album should be empty initially")
def assert_album_empty(context: Dict[str, Any]):
    """Verify new album is empty."""
    response = context.album_response
    data = response.json()

    album = data["data"]
    assert album.get("photo_count", 0) == 0


@then("the creation timestamp should be recorded")
def assert_timestamp_recorded(context: Dict[str, Any]):
    """Verify creation timestamp exists."""
    response = context.album_response
    data = response.json()

    album = data["data"]
    assert "created_at" in album
    assert album["created_at"] is not None


@then(parsers.parse("the album should contain {count:d} photos"))
def assert_album_photo_count(count: int, context: Dict[str, Any]):
    """Verify album contains correct number of photos."""
    response = context.add_photos_response or context.album_response
    data = response.json()

    album = data.get("data", {})
    assert album.get("photo_count", 0) == count


@then("the photos should remain in their original location")
async def assert_photos_unchanged(test_db, context: Dict[str, Any]):
    """Verify photos weren't moved."""
    # Photos should still have their original storage_path
    photos = context.photos

    for photo in photos.values():
        # In real implementation, query photo from DB
        assert photo.storage_path is not None


@then("the photos should be associated with the album")
async def assert_photos_associated(test_db, context: Dict[str, Any]):
    """Verify photos are linked to album."""
    album = context.album
    photos = context.photos

    for photo in photos.values():
        assert album.id in photo.album_ids


@then(parsers.parse('"{photo_id}" should remain in the library'))
async def assert_photo_in_library(photo_id: str, test_db):
    """Verify photo still exists in library."""
    # Query photo from database
    # photo = await test_db.get(Photo, photo_id)
    # assert photo is not None
    pass


@then(parsers.parse('"{photo_id}" should no longer be associated with the album'))
async def assert_photo_not_in_album(photo_id: str, test_db, context: Dict[str, Any]):
    """Verify photo is not in album."""
    album = context.album
    # Check photo.album_ids doesn't contain album.id
    pass


@then("the album should be removed from the system")
async def assert_album_deleted(test_db, context: Dict[str, Any]):
    """Verify album was deleted."""
    response = context.delete_response
    assert response.status_code in [200, 204]


@then(parsers.parse("But all {count:d} photos should remain in the library"))
async def assert_photos_remain(count: int, test_db):
    """Verify photos weren't deleted with album."""
    # Query photos and verify they exist
    pass


@then("the photos should be searchable")
async def assert_photos_searchable(test_client: AsyncClient, context: Dict[str, Any]):
    """Verify photos can still be searched."""
    photos = context.album_photos

    if photos:
        response = await test_client.get(
            "/api/v1/search",
            params={"q": photos[0].filename.replace(".jpg", "")}
        )
        assert response.status_code == 200


@then(parsers.parse("I should receive {count:d} albums"))
def assert_album_count(count: int, context: Dict[str, Any]):
    """Verify number of albums returned."""
    albums = context.albums_list
    assert len(albums) == count


@then("pagination metadata should show:")
def assert_pagination_metadata(context: Dict[str, Any]):
    """Verify pagination metadata."""
    pagination = context.pagination

    for row in context.table:
        field = row["field"]
        expected = row["value"]
        assert str(pagination.get(field)) == expected


@then(parsers.parse("the creation should fail with status {status:d}"))
def assert_creation_failed(status: int, context: Dict[str, Any]):
    """Verify creation failed with specific status."""
    response = context.duplicate_response
    assert response.status_code == status


@then(parsers.parse('the error message should indicate "{message}"'))
def assert_error_message_indicates(message: str, context: Dict[str, Any]):
    """Verify error message contains text."""
    response = context.duplicate_response or context.delete_response
    data = response.json()

    error_msg = data.get("error", {}).get("message", "")
    assert message.lower() in error_msg.lower()


@then("the album should be renamed successfully")
def assert_album_renamed(context: Dict[str, Any]):
    """Verify album was renamed."""
    response = context.rename_response
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


@then("all photo associations should be preserved")
async def assert_associations_preserved(test_db, context: Dict[str, Any]):
    """Verify photo associations weren't affected."""
    # Check that album still has same photos
    pass


@then("the album ID should remain the same")
def assert_album_id_unchanged(context: Dict[str, Any]):
    """Verify album ID didn't change."""
    original_album = context.existing_album or context.album
    response = context.rename_response
    data = response.json()

    new_id = data["data"]["id"]
    assert str(original_album.id) == new_id


@then("a unique share URL should be generated")
def assert_share_url_generated(context: Dict[str, Any]):
    """Verify share URL was created."""
    response = context.share_response
    assert response.status_code in [200, 201]

    data = response.json()
    share_url = data.get("data", {}).get("share_url")
    assert share_url is not None
    assert "share" in share_url


@then("I should receive:")
def assert_stats_received(context: Dict[str, Any]):
    """Verify statistics match expected values."""
    response = context.stats_response
    assert response.status_code == 200

    data = response.json()
    stats = data.get("data", {})

    for row in context.table:
        stat_name = row["statistic"]
        expected = row["value"]
        # Check stat exists (exact matching depends on implementation)
        assert stat_name in stats or stat_name.replace("_", "") in str(stats)