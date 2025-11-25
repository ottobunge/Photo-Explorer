"""Unit tests for batch operations tasks."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.adapters.inbound.workers.tasks.batch_operations import (
    _cleanup_orphans_async,
    _delete_orphaned_files,
    _delete_orphaned_photos,
    _find_orphaned_files,
    _find_orphaned_photos,
    cleanup_orphans_task,
)
from app.domain.entities.photo import Photo


class TestCleanupOrphansTask:
    """Tests for cleanup orphans task."""

    def test_cleanup_orphans_dry_run(self):
        """Should report orphans without deleting anything in dry-run mode."""
        with patch(
            "app.adapters.inbound.workers.tasks.batch_operations.run_async"
        ) as mock_run_async:
            mock_run_async.return_value = {
                "orphaned_photos": ["photo-id-1", "photo-id-2"],
                "orphaned_files": ["/path/to/file1.jpg"],
                "deleted_photo_records": 0,
                "deleted_files": 0,
                "dry_run": True,
            }

            result = cleanup_orphans_task(dry_run=True)

            assert result["dry_run"] is True
            assert len(result["orphaned_photos"]) == 2
            assert len(result["orphaned_files"]) == 1
            assert result["deleted_photo_records"] == 0
            assert result["deleted_files"] == 0

    def test_cleanup_orphans_not_dry_run(self):
        """Should delete orphans when not in dry-run mode."""
        with patch(
            "app.adapters.inbound.workers.tasks.batch_operations.run_async"
        ) as mock_run_async:
            mock_run_async.return_value = {
                "orphaned_photos": ["photo-id-1"],
                "orphaned_files": ["/path/to/file1.jpg"],
                "deleted_photo_records": 1,
                "deleted_files": 1,
                "dry_run": False,
            }

            result = cleanup_orphans_task(dry_run=False, delete_orphaned_files=True)

            assert result["dry_run"] is False
            assert result["deleted_photo_records"] == 1
            assert result["deleted_files"] == 1


class TestFindOrphanedPhotos:
    """Tests for finding orphaned photos."""

    @pytest.mark.asyncio
    async def test_find_orphaned_photos_with_missing_files(self, db_session, tmp_path):
        """Should find photos whose files don't exist on disk."""
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )

        # Create test directory
        test_dir = tmp_path / "storage" / "photos"
        test_dir.mkdir(parents=True)

        # Create a photo with a file that exists
        existing_file = test_dir / "existing.jpg"
        existing_file.write_bytes(b"fake jpg data")

        photo_with_file = Photo.create(
            filename="existing.jpg",
            storage_path="existing.jpg",
        )

        # Create a photo with a missing file
        photo_without_file = Photo.create(
            filename="missing.jpg",
            storage_path="missing.jpg",
        )

        repo = PhotoRepositoryPostgres(db_session)
        await repo.save(photo_with_file)
        await repo.save(photo_without_file)
        await db_session.commit()

        # Mock settings to use our test directory
        with patch("app.adapters.inbound.workers.tasks.batch_operations.settings") as mock_settings:
            mock_settings.storage_photos_path = test_dir

            orphaned = await _find_orphaned_photos(db_session)

            # Only the photo without a file should be found
            assert len(orphaned) == 1
            assert photo_without_file.id.value in orphaned

    @pytest.mark.asyncio
    async def test_find_orphaned_photos_all_files_exist(self, db_session, tmp_path):
        """Should return empty list when all files exist."""
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )

        # Create test directory
        test_dir = tmp_path / "storage" / "photos"
        test_dir.mkdir(parents=True)

        # Create photos with files that exist
        file1 = test_dir / "photo1.jpg"
        file1.write_bytes(b"fake jpg data")

        photo1 = Photo.create(filename="photo1.jpg", storage_path="photo1.jpg")

        repo = PhotoRepositoryPostgres(db_session)
        await repo.save(photo1)
        await db_session.commit()

        # Mock settings
        with patch("app.adapters.inbound.workers.tasks.batch_operations.settings") as mock_settings:
            mock_settings.storage_photos_path = test_dir

            orphaned = await _find_orphaned_photos(db_session)

            assert len(orphaned) == 0


class TestDeleteOrphanedPhotos:
    """Tests for deleting orphaned photos."""

    @pytest.mark.asyncio
    async def test_delete_orphaned_photos(self, db_session):
        """Should delete specified photo records from database."""
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )

        # Create test photos
        photo1 = Photo.create(filename="photo1.jpg", storage_path="photo1.jpg")
        photo2 = Photo.create(filename="photo2.jpg", storage_path="photo2.jpg")

        repo = PhotoRepositoryPostgres(db_session)
        await repo.save(photo1)
        await repo.save(photo2)
        await db_session.commit()

        # Delete one photo
        deleted_count = await _delete_orphaned_photos(db_session, [photo1.id.value])
        await db_session.commit()

        assert deleted_count == 1

        # Verify photo1 is gone, photo2 still exists
        found_photo1 = await repo.find_by_id(photo1.id.value)
        found_photo2 = await repo.find_by_id(photo2.id.value)

        assert found_photo1 is None
        assert found_photo2 is not None

    @pytest.mark.asyncio
    async def test_delete_orphaned_photos_empty_list(self, db_session):
        """Should handle empty list gracefully."""
        deleted_count = await _delete_orphaned_photos(db_session, [])
        assert deleted_count == 0


class TestFindOrphanedFiles:
    """Tests for finding orphaned files."""

    @pytest.mark.asyncio
    async def test_find_orphaned_files(self, db_session, tmp_path):
        """Should find files on disk not tracked in database."""
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )

        # Create test directory with files
        test_dir = tmp_path / "storage" / "photos"
        test_dir.mkdir(parents=True)

        tracked_file = test_dir / "tracked.jpg"
        tracked_file.write_bytes(b"fake jpg data")

        orphaned_file = test_dir / "orphaned.jpg"
        orphaned_file.write_bytes(b"fake jpg data")

        # Create photo only for tracked file
        photo = Photo.create(filename="tracked.jpg", storage_path="tracked.jpg")

        repo = PhotoRepositoryPostgres(db_session)
        await repo.save(photo)
        await db_session.commit()

        # Mock settings
        with patch("app.adapters.inbound.workers.tasks.batch_operations.settings") as mock_settings:
            mock_settings.storage_photos_path = test_dir

            orphaned = await _find_orphaned_files(db_session)

            # Only the orphaned file should be found
            assert len(orphaned) == 1
            assert orphaned[0] == orphaned_file

    @pytest.mark.asyncio
    async def test_find_orphaned_files_ignores_non_images(self, db_session, tmp_path):
        """Should ignore non-image files."""
        test_dir = tmp_path / "storage" / "photos"
        test_dir.mkdir(parents=True)

        # Create non-image files
        text_file = test_dir / "readme.txt"
        text_file.write_bytes(b"some text")

        json_file = test_dir / "data.json"
        json_file.write_bytes(b'{"key": "value"}')

        # Mock settings
        with patch("app.adapters.inbound.workers.tasks.batch_operations.settings") as mock_settings:
            mock_settings.storage_photos_path = test_dir

            orphaned = await _find_orphaned_files(db_session)

            # No files should be found (non-images are ignored)
            assert len(orphaned) == 0

    @pytest.mark.asyncio
    async def test_find_orphaned_files_no_storage_directory(self, db_session, tmp_path):
        """Should handle missing storage directory gracefully."""
        test_dir = tmp_path / "nonexistent"

        # Mock settings
        with patch("app.adapters.inbound.workers.tasks.batch_operations.settings") as mock_settings:
            mock_settings.storage_photos_path = test_dir

            orphaned = await _find_orphaned_files(db_session)

            assert len(orphaned) == 0


class TestDeleteOrphanedFiles:
    """Tests for deleting orphaned files."""

    @pytest.mark.asyncio
    async def test_delete_orphaned_files(self, tmp_path):
        """Should delete specified files from disk."""
        # Create test files
        file1 = tmp_path / "file1.jpg"
        file1.write_bytes(b"data")

        file2 = tmp_path / "file2.jpg"
        file2.write_bytes(b"data")

        # Delete one file
        deleted_count = await _delete_orphaned_files([file1])

        assert deleted_count == 1
        assert not file1.exists()
        assert file2.exists()

    @pytest.mark.asyncio
    async def test_delete_orphaned_files_handles_missing_files(self, tmp_path):
        """Should handle files that don't exist without error."""
        nonexistent = tmp_path / "nonexistent.jpg"

        deleted_count = await _delete_orphaned_files([nonexistent])

        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_orphaned_files_empty_list(self):
        """Should handle empty list gracefully."""
        deleted_count = await _delete_orphaned_files([])
        assert deleted_count == 0


class TestCleanupOrphansIntegration:
    """Integration tests for cleanup orphans."""

    @pytest.mark.asyncio
    async def test_full_cleanup_flow_dry_run(self, db_session, tmp_path):
        """Should perform complete cleanup in dry-run mode."""
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )

        # Setup test environment
        test_dir = tmp_path / "storage" / "photos"
        test_dir.mkdir(parents=True)

        # Create orphaned photo (no file)
        orphaned_photo = Photo.create(
            filename="missing.jpg",
            storage_path="missing.jpg",
        )

        # Create tracked photo with file
        tracked_file = test_dir / "tracked.jpg"
        tracked_file.write_bytes(b"data")
        tracked_photo = Photo.create(
            filename="tracked.jpg",
            storage_path="tracked.jpg",
        )

        # Create orphaned file (not in DB)
        orphaned_file = test_dir / "orphaned.jpg"
        orphaned_file.write_bytes(b"data")

        repo = PhotoRepositoryPostgres(db_session)
        await repo.save(orphaned_photo)
        await repo.save(tracked_photo)
        await db_session.commit()

        # Mock settings
        with patch("app.adapters.inbound.workers.tasks.batch_operations.settings") as mock_settings:
            mock_settings.storage_photos_path = test_dir

            # Run cleanup in dry-run mode
            result = await _cleanup_orphans_async(dry_run=True, delete_orphaned_files=False)

            # Verify results
            assert result["dry_run"] is True
            assert len(result["orphaned_photos"]) == 1
            assert len(result["orphaned_files"]) == 1
            assert result["deleted_photo_records"] == 0
            assert result["deleted_files"] == 0

            # Verify nothing was actually deleted
            found_orphaned = await repo.find_by_id(orphaned_photo.id.value)
            assert found_orphaned is not None
            assert orphaned_file.exists()

    @pytest.mark.asyncio
    async def test_full_cleanup_flow_not_dry_run(self, db_session, tmp_path):
        """Should perform complete cleanup and delete orphans."""
        from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
            PhotoRepositoryPostgres,
        )

        # Setup test environment
        test_dir = tmp_path / "storage" / "photos"
        test_dir.mkdir(parents=True)

        # Create orphaned photo (no file)
        orphaned_photo = Photo.create(
            filename="missing.jpg",
            storage_path="missing.jpg",
        )

        # Create orphaned file (not in DB)
        orphaned_file = test_dir / "orphaned.jpg"
        orphaned_file.write_bytes(b"data")

        repo = PhotoRepositoryPostgres(db_session)
        await repo.save(orphaned_photo)
        await db_session.commit()

        # Mock settings
        with patch("app.adapters.inbound.workers.tasks.batch_operations.settings") as mock_settings:
            mock_settings.storage_photos_path = test_dir

            # Run cleanup for real
            result = await _cleanup_orphans_async(dry_run=False, delete_orphaned_files=True)

            # Verify results
            assert result["dry_run"] is False
            assert result["deleted_photo_records"] == 1
            assert result["deleted_files"] == 1

            # Verify orphans were actually deleted
            found_orphaned = await repo.find_by_id(orphaned_photo.id.value)
            assert found_orphaned is None
            assert not orphaned_file.exists()
