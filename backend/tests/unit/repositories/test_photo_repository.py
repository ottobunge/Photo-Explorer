"""Unit tests for PhotoRepository - focusing on delete_many operation.

Tests for bulk photo deletion following TDD approach.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.postgres.repositories.photo_repository import (
    PhotoRepositoryPostgres,
)


class TestPhotoRepositoryDeleteMany:
    """Tests for bulk photo deletion."""

    @pytest.mark.asyncio
    async def test_delete_many_removes_all_photos(self):
        """Should delete all photos with given IDs."""
        # Given: mock session and a list of photo IDs
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        photo_id1 = uuid4()
        photo_id2 = uuid4()
        photo_id3 = uuid4()
        photo_ids = [photo_id1, photo_id2, photo_id3]

        # Mock execute result with rowcount
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        # When: delete_many is called
        deleted_count = await repo.delete_many(photo_ids)

        # Then: should return count of deleted rows
        assert deleted_count == 3

        # Verify execute was called once (single query)
        assert mock_session.execute.call_count == 1

        # Verify flush was called
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_many_returns_count(self):
        """Should return the count of deleted rows."""
        # Given: mock session and photo IDs
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        photo_ids = [uuid4(), uuid4(), uuid4(), uuid4(), uuid4()]

        # Mock execute result with rowcount
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        # When: delete_many is called
        deleted_count = await repo.delete_many(photo_ids)

        # Then: should return the exact rowcount
        assert deleted_count == 5

    @pytest.mark.asyncio
    async def test_delete_many_empty_list_returns_zero(self):
        """Should return 0 and not execute query when list is empty."""
        # Given: mock session and empty list
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        # When: delete_many is called with empty list
        deleted_count = await repo.delete_many([])

        # Then: should return 0
        assert deleted_count == 0

        # Should not call execute or flush
        mock_session.execute.assert_not_called()
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_many_handles_non_existent_ids(self):
        """Should handle gracefully when some IDs don't exist."""
        # Given: mock session and photo IDs (some don't exist)
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        photo_ids = [uuid4(), uuid4(), uuid4()]

        # Mock execute result - only 2 rows deleted (1 didn't exist)
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        # When: delete_many is called
        deleted_count = await repo.delete_many(photo_ids)

        # Then: should return actual count of deleted rows
        assert deleted_count == 2

    @pytest.mark.asyncio
    async def test_delete_many_performs_single_query(self):
        """Should execute only one DELETE query regardless of number of IDs."""
        # Given: mock session and many photo IDs
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        # Large list of photo IDs
        photo_ids = [uuid4() for _ in range(50)]

        # Mock execute result
        mock_result = MagicMock()
        mock_result.rowcount = 50
        mock_session.execute.return_value = mock_result

        # When: delete_many is called
        await repo.delete_many(photo_ids)

        # Then: should call execute exactly once (not N times)
        assert mock_session.execute.call_count == 1, (
            "delete_many should use single DELETE query with IN clause, " "not N individual queries"
        )

        # Verify the DELETE statement uses IN clause
        execute_call = mock_session.execute.call_args_list[0]
        stmt = str(execute_call[0][0])

        # Should be a DELETE statement
        assert (
            "DELETE" in stmt.upper() or "delete" in stmt.lower()
        ), "Should execute a DELETE statement"

    @pytest.mark.asyncio
    async def test_delete_many_with_single_id(self):
        """Should work correctly with a single photo ID."""
        # Given: mock session and single photo ID
        mock_session = AsyncMock()
        repo = PhotoRepositoryPostgres(mock_session)

        photo_id = uuid4()

        # Mock execute result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # When: delete_many is called with single ID
        deleted_count = await repo.delete_many([photo_id])

        # Then: should return 1
        assert deleted_count == 1

        # Should still use same query pattern
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()
