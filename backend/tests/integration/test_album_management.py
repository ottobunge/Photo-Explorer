"""Integration tests for album management.

Tests:
1. Create album
2. Add photos to album
3. Remove photos from album
4. Delete album
5. Cascade behavior
"""


import pytest
from sqlalchemy import select

from app.adapters.outbound.persistence.postgres.models import photo_album_association
from app.adapters.outbound.persistence.postgres.repositories import (
    AlbumRepositoryPostgres,
    PhotoRepositoryPostgres,
)
from tests.integration.factories import AlbumFactory, PhotoFactory


class TestAlbumManagement:
    """Test album CRUD operations and photo associations."""

    @pytest.mark.asyncio
    async def test_create_album(
        self,
        test_session,
    ):
        """Test creating a new album."""
        album_repo = AlbumRepositoryPostgres(test_session)

        # 1. Create album
        album = AlbumFactory.create(
            name="My Vacation Photos",
            description="Summer vacation 2024",
        )
        saved_album = await album_repo.save(album)

        # 2. Verify album is saved
        assert saved_album.id.value == album.id.value
        assert saved_album.name == "My Vacation Photos"
        assert saved_album.description == "Summer vacation 2024"

        # 3. Retrieve album
        retrieved = await album_repo.find_by_id(album.id.value)
        assert retrieved is not None
        assert retrieved.name == "My Vacation Photos"

    @pytest.mark.asyncio
    async def test_add_photos_to_album(
        self,
        test_session,
    ):
        """Test adding photos to an album."""
        album_repo = AlbumRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create album
        album = AlbumFactory.create(name="Test Album")
        album = await album_repo.save(album)

        # 2. Create photos
        photos = PhotoFactory.create_batch(3)
        saved_photos = []
        for photo in photos:
            saved = await photo_repo.save(photo)
            saved_photos.append(saved)

        # 3. Add photos to album
        photo_ids = [p.id.value for p in saved_photos]
        album.photo_ids = photo_ids
        updated_album = await album_repo.save(album)

        # 4. Verify photos are associated with album
        assert len(updated_album.photo_ids) == 3
        assert set(updated_album.photo_ids) == set(photo_ids)

        # 5. Verify from photo side
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(photo_id)
            assert album.id.value in photo.album_ids

    @pytest.mark.asyncio
    async def test_remove_photos_from_album(
        self,
        test_session,
    ):
        """Test removing photos from an album."""
        album_repo = AlbumRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create album with photos
        photos = PhotoFactory.create_batch(5)
        saved_photos = []
        for photo in photos:
            saved = await photo_repo.save(photo)
            saved_photos.append(saved)

        photo_ids = [p.id.value for p in saved_photos]
        album = AlbumFactory.create(
            name="Album to Modify",
            photo_ids=photo_ids,
        )
        album = await album_repo.save(album)

        # 2. Verify all photos are in album
        retrieved = await album_repo.find_by_id(album.id.value)
        assert len(retrieved.photo_ids) == 5

        # 3. Remove 2 photos
        photos_to_keep = photo_ids[:3]
        album.photo_ids = photos_to_keep
        updated = await album_repo.save(album)

        # 4. Verify only 3 photos remain
        assert len(updated.photo_ids) == 3
        assert set(updated.photo_ids) == set(photos_to_keep)

        # 5. Verify removed photos no longer reference album
        removed_photo_id = photo_ids[3]
        removed_photo = await photo_repo.find_by_id(removed_photo_id)
        assert album.id.value not in removed_photo.album_ids

    @pytest.mark.asyncio
    async def test_delete_album(
        self,
        test_session,
    ):
        """Test deleting an album."""
        album_repo = AlbumRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create album with photos
        photos = PhotoFactory.create_batch(3)
        saved_photos = []
        for photo in photos:
            saved = await photo_repo.save(photo)
            saved_photos.append(saved)

        photo_ids = [p.id.value for p in saved_photos]
        album = AlbumFactory.create(photo_ids=photo_ids)
        album = await album_repo.save(album)

        # 2. Verify album exists
        assert await album_repo.find_by_id(album.id.value) is not None

        # 3. Delete album
        await album_repo.delete(album.id.value)
        await test_session.commit()

        # 4. Verify album is deleted
        assert await album_repo.find_by_id(album.id.value) is None

        # 5. Verify photos still exist (no cascade delete of photos)
        for photo_id in photo_ids:
            photo = await photo_repo.find_by_id(photo_id)
            assert photo is not None
            # Photo should no longer reference the deleted album
            assert album.id.value not in photo.album_ids

    @pytest.mark.asyncio
    async def test_album_cascade_delete_associations(
        self,
        test_session,
    ):
        """Test that album deletion cascades to photo-album associations."""
        album_repo = AlbumRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create album with photos
        photos = PhotoFactory.create_batch(3)
        photo_ids = []
        for photo in photos:
            saved = await photo_repo.save(photo)
            photo_ids.append(saved.id.value)

        album = AlbumFactory.create(photo_ids=photo_ids)
        album = await album_repo.save(album)
        await test_session.commit()

        # 2. Verify associations exist in junction table
        stmt = select(photo_album_association).where(
            photo_album_association.c.album_id == album.id.value
        )
        result = await test_session.execute(stmt)
        associations_before = result.all()
        assert len(associations_before) == 3

        # 3. Delete album
        await album_repo.delete(album.id.value)
        await test_session.commit()

        # 4. Verify associations are deleted (cascade)
        result_after = await test_session.execute(stmt)
        associations_after = result_after.all()
        assert len(associations_after) == 0

    @pytest.mark.asyncio
    async def test_album_with_cover_photo(
        self,
        test_session,
    ):
        """Test album with cover photo."""
        album_repo = AlbumRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create photos
        photos = PhotoFactory.create_batch(3)
        saved_photos = []
        for photo in photos:
            saved = await photo_repo.save(photo)
            saved_photos.append(saved)

        # 2. Create album with first photo as cover
        photo_ids = [p.id.value for p in saved_photos]
        cover_photo_id = photo_ids[0]

        album = AlbumFactory.create(
            name="Album with Cover",
            photo_ids=photo_ids,
            cover_photo_id=cover_photo_id,
        )
        album = await album_repo.save(album)

        # 3. Verify cover photo is set
        retrieved = await album_repo.find_by_id(album.id.value)
        assert retrieved.cover_photo_id == cover_photo_id

        # 4. Change cover photo
        new_cover_id = photo_ids[1]
        album.cover_photo_id = new_cover_id
        updated = await album_repo.save(album)
        assert updated.cover_photo_id == new_cover_id

    @pytest.mark.asyncio
    async def test_find_albums_by_photo(
        self,
        test_session,
    ):
        """Test finding all albums containing a specific photo."""
        album_repo = AlbumRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create a photo
        photo = PhotoFactory.create()
        photo = await photo_repo.save(photo)

        # 2. Create multiple albums containing this photo
        album1 = AlbumFactory.create(
            name="Album 1",
            photo_ids=[photo.id.value],
        )
        album2 = AlbumFactory.create(
            name="Album 2",
            photo_ids=[photo.id.value],
        )
        album3 = AlbumFactory.create(
            name="Album 3 (no photo)",
            photo_ids=[],
        )

        await album_repo.save(album1)
        await album_repo.save(album2)
        await album_repo.save(album3)

        # 3. Find albums containing the photo
        albums = await album_repo.find_by_photo_id(photo.id.value)

        # 4. Verify correct albums are returned
        assert len(albums) == 2
        album_names = {a.name for a in albums}
        assert "Album 1" in album_names
        assert "Album 2" in album_names
        assert "Album 3 (no photo)" not in album_names

    @pytest.mark.asyncio
    async def test_update_album_metadata(
        self,
        test_session,
    ):
        """Test updating album name and description."""
        album_repo = AlbumRepositoryPostgres(test_session)

        # 1. Create album
        album = AlbumFactory.create(
            name="Original Name",
            description="Original description",
        )
        album = await album_repo.save(album)

        # 2. Update metadata
        album.name = "Updated Name"
        album.description = "Updated description"
        updated = await album_repo.save(album)

        # 3. Verify updates
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"

        # 4. Retrieve and verify
        retrieved = await album_repo.find_by_id(album.id.value)
        assert retrieved.name == "Updated Name"
        assert retrieved.description == "Updated description"

    @pytest.mark.asyncio
    async def test_album_photo_count(
        self,
        test_session,
    ):
        """Test getting photo count for albums."""
        album_repo = AlbumRepositoryPostgres(test_session)
        photo_repo = PhotoRepositoryPostgres(test_session)

        # 1. Create albums with different photo counts
        # Album 1: 5 photos
        photos1 = PhotoFactory.create_batch(5)
        photo_ids1 = []
        for photo in photos1:
            saved = await photo_repo.save(photo)
            photo_ids1.append(saved.id.value)

        album1 = AlbumFactory.create(
            name="Album with 5 photos",
            photo_ids=photo_ids1,
        )
        album1 = await album_repo.save(album1)

        # Album 2: 0 photos
        album2 = AlbumFactory.create(
            name="Empty Album",
            photo_ids=[],
        )
        album2 = await album_repo.save(album2)

        # 2. Verify photo counts
        retrieved1 = await album_repo.find_by_id(album1.id.value)
        assert len(retrieved1.photo_ids) == 5

        retrieved2 = await album_repo.find_by_id(album2.id.value)
        assert len(retrieved2.photo_ids) == 0

    @pytest.mark.asyncio
    async def test_find_all_albums(
        self,
        test_session,
    ):
        """Test retrieving all albums."""
        album_repo = AlbumRepositoryPostgres(test_session)

        # 1. Create multiple albums
        albums = AlbumFactory.create_batch(5)
        for album in albums:
            await album_repo.save(album)

        # 2. Retrieve all albums
        all_albums = await album_repo.find_all(limit=10)

        # 3. Verify count
        assert len(all_albums) >= 5

    @pytest.mark.asyncio
    async def test_album_pagination(
        self,
        test_session,
    ):
        """Test paginating through albums."""
        album_repo = AlbumRepositoryPostgres(test_session)

        # 1. Create many albums
        albums = AlbumFactory.create_batch(15)
        for album in albums:
            await album_repo.save(album)

        # 2. Get first page
        page1 = await album_repo.find_all(limit=5, offset=0)
        assert len(page1) == 5

        # 3. Get second page
        page2 = await album_repo.find_all(limit=5, offset=5)
        assert len(page2) == 5

        # 4. Verify different albums in each page
        page1_ids = {a.id.value for a in page1}
        page2_ids = {a.id.value for a in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
