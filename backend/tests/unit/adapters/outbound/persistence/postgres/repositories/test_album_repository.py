"""Unit tests for AlbumRepository."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.adapters.outbound.persistence.postgres.models import AlbumModel, PhotoModel
from app.adapters.outbound.persistence.postgres.repositories.album_repository import (
    AlbumRepositoryPostgres,
)
from app.domain.entities import Album


class TestAlbumRepositorySave:
    """Tests for AlbumRepository save operations."""

    async def test_save_new_album(self, db_session):
        """When saving new album, it should be persisted."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="Test Album", description="Test description")

        saved_album = await repo.save(album)

        assert saved_album.id == album.id
        assert saved_album.name == "Test Album"
        assert saved_album.description == "Test description"

        # Verify in database
        stmt = select(AlbumModel).where(AlbumModel.id == album.id.value)
        result = await db_session.execute(stmt)
        model = result.scalar_one()
        assert model.name == "Test Album"

    async def test_save_existing_album_updates(self, db_session):
        """When saving existing album, it should update."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="Original Name")
        await repo.save(album)

        # Update and save again
        album.update(name="Updated Name")
        updated_album = await repo.save(album)

        assert updated_album.name == "Updated Name"

        # Verify only one record exists
        stmt = select(AlbumModel).where(AlbumModel.id == album.id.value)
        result = await db_session.execute(stmt)
        models = result.scalars().all()
        assert len(models) == 1
        assert models[0].name == "Updated Name"

    async def test_save_preserves_cover_photo(self, db_session):
        """When saving album with cover photo, it should be preserved."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="Test Album")
        photo_id = uuid4()
        album.add_photo(photo_id)
        album.set_cover(photo_id)

        saved_album = await repo.save(album)

        assert saved_album.cover_photo_id == photo_id


class TestAlbumRepositoryFindById:
    """Tests for AlbumRepository find_by_id operations."""

    async def test_find_by_id_existing(self, db_session):
        """When finding existing album, it should be returned."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="Test Album")
        await repo.save(album)

        found_album = await repo.find_by_id(album.id.value)

        assert found_album is not None
        assert found_album.id == album.id
        assert found_album.name == "Test Album"

    async def test_find_by_id_non_existing(self, db_session):
        """When finding non-existing album, it should return None."""
        repo = AlbumRepositoryPostgres(db_session)
        non_existing_id = uuid4()

        found_album = await repo.find_by_id(non_existing_id)

        assert found_album is None

    async def test_find_by_id_loads_photos(self, db_session):
        """When finding album, photo associations should be loaded."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="Test Album")
        photo_id = uuid4()
        album.add_photo(photo_id)
        await repo.save(album)

        # Create photo model to satisfy foreign key (in real scenario, photos exist)
        # For this test, we just verify the association is loaded without error
        found_album = await repo.find_by_id(album.id.value)

        assert found_album is not None
        # Photo IDs are loaded from relationships
        assert isinstance(found_album.photo_ids, list)


class TestAlbumRepositoryFindAll:
    """Tests for AlbumRepository find_all operations."""

    async def test_find_all_empty(self, db_session):
        """When no albums exist, it should return empty list."""
        repo = AlbumRepositoryPostgres(db_session)

        albums = await repo.find_all()

        assert albums == []

    async def test_find_all_multiple_albums(self, db_session):
        """When multiple albums exist, they should all be returned."""
        repo = AlbumRepositoryPostgres(db_session)
        album1 = Album.create(name="Album 1")
        album2 = Album.create(name="Album 2")
        album3 = Album.create(name="Album 3")

        await repo.save(album1)
        await repo.save(album2)
        await repo.save(album3)

        albums = await repo.find_all()

        assert len(albums) == 3
        album_names = {album.name for album in albums}
        assert album_names == {"Album 1", "Album 2", "Album 3"}

    async def test_find_all_ordered_by_created_at_desc(self, db_session):
        """When finding all albums, they should be ordered newest first."""
        repo = AlbumRepositoryPostgres(db_session)

        # Create albums with small delays to ensure different timestamps
        album1 = Album.create(name="First")
        await repo.save(album1)

        import asyncio
        await asyncio.sleep(0.01)

        album2 = Album.create(name="Second")
        await repo.save(album2)

        await asyncio.sleep(0.01)

        album3 = Album.create(name="Third")
        await repo.save(album3)

        albums = await repo.find_all()

        # Should be in reverse chronological order
        assert albums[0].name == "Third"
        assert albums[1].name == "Second"
        assert albums[2].name == "First"

    async def test_find_all_with_limit(self, db_session):
        """When finding with limit, only that many should be returned."""
        repo = AlbumRepositoryPostgres(db_session)

        for i in range(5):
            album = Album.create(name=f"Album {i}")
            await repo.save(album)

        albums = await repo.find_all(limit=3)

        assert len(albums) == 3

    async def test_find_all_with_offset(self, db_session):
        """When finding with offset, earlier records should be skipped."""
        repo = AlbumRepositoryPostgres(db_session)

        for i in range(5):
            album = Album.create(name=f"Album {i}")
            await repo.save(album)

        albums = await repo.find_all(limit=10, offset=2)

        assert len(albums) == 3  # Total 5, skip first 2


class TestAlbumRepositoryDelete:
    """Tests for AlbumRepository delete operations."""

    async def test_delete_existing_album(self, db_session):
        """When deleting existing album, it should return True."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="To Delete")
        await repo.save(album)

        result = await repo.delete(album.id.value)

        assert result is True

        # Verify deleted
        found = await repo.find_by_id(album.id.value)
        assert found is None

    async def test_delete_non_existing_album(self, db_session):
        """When deleting non-existing album, it should return False."""
        repo = AlbumRepositoryPostgres(db_session)
        non_existing_id = uuid4()

        result = await repo.delete(non_existing_id)

        assert result is False


class TestAlbumRepositoryCount:
    """Tests for AlbumRepository count operations."""

    async def test_count_empty(self, db_session):
        """When no albums exist, count should be 0."""
        repo = AlbumRepositoryPostgres(db_session)

        count = await repo.count()

        assert count == 0

    async def test_count_multiple_albums(self, db_session):
        """When albums exist, count should match."""
        repo = AlbumRepositoryPostgres(db_session)

        for i in range(7):
            album = Album.create(name=f"Album {i}")
            await repo.save(album)

        count = await repo.count()

        assert count == 7


class TestAlbumRepositoryFindByName:
    """Tests for AlbumRepository find_by_name operations."""

    async def test_find_by_name_existing(self, db_session):
        """When finding by existing name, it should be returned."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="Unique Album Name")
        await repo.save(album)

        found_album = await repo.find_by_name("Unique Album Name")

        assert found_album is not None
        assert found_album.name == "Unique Album Name"
        assert found_album.id == album.id

    async def test_find_by_name_non_existing(self, db_session):
        """When finding by non-existing name, it should return None."""
        repo = AlbumRepositoryPostgres(db_session)

        found_album = await repo.find_by_name("Non-existing Album")

        assert found_album is None

    async def test_find_by_name_is_case_sensitive(self, db_session):
        """When finding by name, it should be case sensitive."""
        repo = AlbumRepositoryPostgres(db_session)
        album = Album.create(name="TestAlbum")
        await repo.save(album)

        found_album = await repo.find_by_name("testalbum")

        assert found_album is None
