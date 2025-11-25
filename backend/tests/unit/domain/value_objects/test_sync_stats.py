"""Unit tests for SyncStats value object."""

from datetime import datetime

import pytest

from app.domain.value_objects.sync_stats import SyncStats


class TestSyncStatsCreation:
    """Test SyncStats creation and initialization."""

    def test_sync_stats_creation_with_defaults(self):
        """Test creating SyncStats with default values."""
        stats = SyncStats()

        assert stats.total_items == 0
        assert stats.indexed == 0
        assert stats.skipped == 0
        assert stats.failed == 0
        assert stats.started_at is None
        assert stats.completed_at is None

    def test_sync_stats_creation_with_values(self):
        """Test creating SyncStats with provided values."""
        started = datetime(2025, 11, 25, 10, 0, 0)
        completed = datetime(2025, 11, 25, 10, 5, 30)

        stats = SyncStats(
            total_items=100,
            indexed=85,
            skipped=10,
            failed=5,
            started_at=started,
            completed_at=completed,
        )

        assert stats.total_items == 100
        assert stats.indexed == 85
        assert stats.skipped == 10
        assert stats.failed == 5
        assert stats.started_at == started
        assert stats.completed_at == completed

    def test_sync_stats_is_immutable(self):
        """Test that SyncStats is immutable (frozen dataclass)."""
        stats = SyncStats(total_items=50)

        with pytest.raises(AttributeError):
            stats.total_items = 100  # Should raise error for frozen dataclass


class TestDurationCalculation:
    """Test duration calculation property."""

    def test_duration_calculation_with_both_timestamps(self):
        """Test duration calculation when both timestamps are present."""
        started = datetime(2025, 11, 25, 10, 0, 0)
        completed = datetime(2025, 11, 25, 10, 5, 30)

        stats = SyncStats(
            started_at=started,
            completed_at=completed,
        )

        # 5 minutes 30 seconds = 330 seconds
        assert stats.duration_seconds == 330.0

    def test_duration_calculation_without_started_at(self):
        """Test duration calculation when started_at is None."""
        stats = SyncStats(
            completed_at=datetime(2025, 11, 25, 10, 5, 30),
        )

        assert stats.duration_seconds is None

    def test_duration_calculation_without_completed_at(self):
        """Test duration calculation when completed_at is None."""
        stats = SyncStats(
            started_at=datetime(2025, 11, 25, 10, 0, 0),
        )

        assert stats.duration_seconds is None

    def test_duration_calculation_without_timestamps(self):
        """Test duration calculation when both timestamps are None."""
        stats = SyncStats()

        assert stats.duration_seconds is None

    def test_duration_calculation_with_fractional_seconds(self):
        """Test duration calculation preserves fractional seconds."""
        started = datetime(2025, 11, 25, 10, 0, 0, 0)
        completed = datetime(2025, 11, 25, 10, 0, 0, 500000)  # 0.5 seconds

        stats = SyncStats(
            started_at=started,
            completed_at=completed,
        )

        assert stats.duration_seconds == 0.5


class TestIsCompleteProperty:
    """Test is_complete property."""

    def test_is_complete_when_completed_at_is_set(self):
        """Test is_complete returns True when completed_at is set."""
        stats = SyncStats(
            completed_at=datetime(2025, 11, 25, 10, 5, 30),
        )

        assert stats.is_complete is True

    def test_is_complete_when_completed_at_is_none(self):
        """Test is_complete returns False when completed_at is None."""
        stats = SyncStats(
            started_at=datetime(2025, 11, 25, 10, 0, 0),
        )

        assert stats.is_complete is False

    def test_is_complete_for_default_stats(self):
        """Test is_complete returns False for default stats."""
        stats = SyncStats()

        assert stats.is_complete is False


class TestSuccessRateCalculation:
    """Test success_rate calculation property."""

    def test_success_rate_with_all_successful(self):
        """Test success rate when all items are successful."""
        stats = SyncStats(
            total_items=100,
            indexed=100,
            skipped=0,
            failed=0,
        )

        assert stats.success_rate == 1.0

    def test_success_rate_with_mixed_results(self):
        """Test success rate with mixed success/failure."""
        stats = SyncStats(
            total_items=100,
            indexed=80,
            skipped=15,
            failed=5,
        )

        # Success rate = (indexed + skipped) / total_items = 95 / 100 = 0.95
        assert stats.success_rate == 0.95

    def test_success_rate_with_all_failed(self):
        """Test success rate when all items failed."""
        stats = SyncStats(
            total_items=100,
            indexed=0,
            skipped=0,
            failed=100,
        )

        assert stats.success_rate == 0.0

    def test_success_rate_with_no_items(self):
        """Test success rate when total_items is zero."""
        stats = SyncStats(
            total_items=0,
            indexed=0,
            skipped=0,
            failed=0,
        )

        # When there are no items, success rate should be 1.0 (100%)
        assert stats.success_rate == 1.0

    def test_success_rate_with_only_skipped(self):
        """Test success rate when only items are skipped (no failures)."""
        stats = SyncStats(
            total_items=50,
            indexed=0,
            skipped=50,
            failed=0,
        )

        # Skipped items count as successful
        assert stats.success_rate == 1.0

    def test_success_rate_partial_failure(self):
        """Test success rate with partial failure."""
        stats = SyncStats(
            total_items=200,
            indexed=150,
            skipped=30,
            failed=20,
        )

        # Success rate = (150 + 30) / 200 = 0.9
        assert stats.success_rate == 0.9


class TestToDictSerialization:
    """Test to_dict serialization method."""

    def test_to_dict_with_complete_stats(self):
        """Test to_dict serialization with complete stats."""
        started = datetime(2025, 11, 25, 10, 0, 0)
        completed = datetime(2025, 11, 25, 10, 5, 30)

        stats = SyncStats(
            total_items=100,
            indexed=85,
            skipped=10,
            failed=5,
            started_at=started,
            completed_at=completed,
        )

        result = stats.to_dict()

        assert result == {
            "total_items": 100,
            "indexed": 85,
            "skipped": 10,
            "failed": 5,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": 330.0,
            "is_complete": True,
            "success_rate": 0.95,
        }

    def test_to_dict_with_minimal_stats(self):
        """Test to_dict serialization with minimal stats (defaults)."""
        stats = SyncStats()

        result = stats.to_dict()

        assert result == {
            "total_items": 0,
            "indexed": 0,
            "skipped": 0,
            "failed": 0,
            "started_at": None,
            "completed_at": None,
            "duration_seconds": None,
            "is_complete": False,
            "success_rate": 1.0,  # No items means 100% success
        }

    def test_to_dict_with_in_progress_sync(self):
        """Test to_dict serialization for in-progress sync."""
        started = datetime(2025, 11, 25, 10, 0, 0)

        stats = SyncStats(
            total_items=100,
            indexed=50,
            skipped=5,
            failed=2,
            started_at=started,
            completed_at=None,
        )

        result = stats.to_dict()

        assert result == {
            "total_items": 100,
            "indexed": 50,
            "skipped": 5,
            "failed": 2,
            "started_at": started.isoformat(),
            "completed_at": None,
            "duration_seconds": None,
            "is_complete": False,
            "success_rate": 0.55,  # (50 + 5) / 100
        }

    def test_to_dict_datetime_serialization(self):
        """Test that datetime objects are properly serialized to ISO format."""
        started = datetime(2025, 11, 25, 10, 0, 0, 123456)
        completed = datetime(2025, 11, 25, 10, 5, 30, 654321)

        stats = SyncStats(
            started_at=started,
            completed_at=completed,
        )

        result = stats.to_dict()

        # Verify ISO format strings
        assert result["started_at"] == "2025-11-25T10:00:00.123456"
        assert result["completed_at"] == "2025-11-25T10:05:30.654321"
        assert isinstance(result["started_at"], str)
        assert isinstance(result["completed_at"], str)
