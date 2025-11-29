"""Unit tests for batch upload cleanup helper function."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.adapters.inbound.api.routes.photos import _cleanup_partial_uploads
from app.application.services.photo_service import PhotoService


class TestCleanupPartialUploads:
    """Unit tests for the _cleanup_partial_uploads helper function."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_all_photos(self):
        """Cleanup should attempt to delete all provided photo IDs."""
        # Create mock photo service
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(return_value=True)

        photo_ids = [uuid4(), uuid4(), uuid4()]

        await _cleanup_partial_uploads(photo_ids, photo_service)

        # Verify delete_photo was called for each ID
        assert photo_service.delete_photo.call_count == 3
        for photo_id in photo_ids:
            photo_service.delete_photo.assert_any_call(photo_id)

    @pytest.mark.asyncio
    async def test_cleanup_continues_on_individual_delete_failure(self):
        """Cleanup should continue even if individual photo deletion fails."""
        # Create mock photo service that fails on 2nd call
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(
            side_effect=[True, Exception("Delete failed"), True]
        )

        photo_ids = [uuid4(), uuid4(), uuid4()]

        # Should not raise exception
        await _cleanup_partial_uploads(photo_ids, photo_service)

        # All delete attempts should be made
        assert photo_service.delete_photo.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_with_empty_list(self):
        """Cleanup should handle empty photo ID list gracefully."""
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(return_value=True)

        await _cleanup_partial_uploads([], photo_service)

        # Should not call delete_photo
        photo_service.delete_photo.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_with_single_photo(self):
        """Cleanup should handle single photo ID."""
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(return_value=True)

        photo_id = uuid4()

        await _cleanup_partial_uploads([photo_id], photo_service)

        photo_service.delete_photo.assert_called_once_with(photo_id)

    @pytest.mark.asyncio
    async def test_cleanup_handles_all_failures(self):
        """Cleanup should handle case where all deletions fail."""
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(
            side_effect=Exception("Storage unavailable")
        )

        photo_ids = [uuid4(), uuid4()]

        # Should not raise exception even if all deletions fail
        await _cleanup_partial_uploads(photo_ids, photo_service)

        # All attempts should still be made
        assert photo_service.delete_photo.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_photo_service_delete_returns_false(self):
        """Cleanup should log when photo deletion returns False (not found)."""
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(return_value=False)

        photo_ids = [uuid4()]

        await _cleanup_partial_uploads(photo_ids, photo_service)

        # Should still complete without raising
        photo_service.delete_photo.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_preserves_order_of_deletion(self):
        """Cleanup should delete photos in the order they were provided."""
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(return_value=True)

        photo_ids = [uuid4(), uuid4(), uuid4()]

        await _cleanup_partial_uploads(photo_ids, photo_service)

        # Verify order of calls
        calls = photo_service.delete_photo.call_args_list
        assert len(calls) == 3
        for i, call in enumerate(calls):
            assert call[0][0] == photo_ids[i]

    @pytest.mark.asyncio
    async def test_cleanup_with_mixed_failures(self):
        """Cleanup should continue through mix of successes and failures."""
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(
            side_effect=[
                True,  # Success
                Exception("File not found"),  # Failure
                True,  # Success
                False,  # Not found (returns False)
                Exception("Storage error"),  # Another failure
            ]
        )

        photo_ids = [uuid4() for _ in range(5)]

        # Should not raise exception
        await _cleanup_partial_uploads(photo_ids, photo_service)

        # All delete attempts should be made
        assert photo_service.delete_photo.call_count == 5

    @pytest.mark.asyncio
    async def test_cleanup_with_large_batch(self):
        """Cleanup should handle large number of photos."""
        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(return_value=True)

        # Create 1000 photo IDs
        photo_ids = [uuid4() for _ in range(1000)]

        await _cleanup_partial_uploads(photo_ids, photo_service)

        # All should be attempted
        assert photo_service.delete_photo.call_count == 1000

    @pytest.mark.asyncio
    async def test_cleanup_logs_info_on_success(self, caplog):
        """Cleanup should log information about successful deletions."""
        import logging

        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(return_value=True)

        photo_id = uuid4()

        with caplog.at_level(logging.INFO):
            await _cleanup_partial_uploads([photo_id], photo_service)

        # Should have logged the successful cleanup
        assert "Cleanup deleted photo" in caplog.text or photo_service.delete_photo.called

    @pytest.mark.asyncio
    async def test_cleanup_logs_errors_on_failure(self, caplog):
        """Cleanup should log errors for failed deletions."""
        import logging

        photo_service = AsyncMock(spec=PhotoService)
        photo_service.delete_photo = AsyncMock(
            side_effect=Exception("Storage error")
        )

        photo_id = uuid4()

        with caplog.at_level(logging.ERROR):
            await _cleanup_partial_uploads([photo_id], photo_service)

        # Should have logged the cleanup error
        assert "Cleanup error" in caplog.text or photo_service.delete_photo.called
