"""SyncStats value object - Statistics for sync operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SyncStats:
    """
    Immutable statistics for a sync operation.

    This value object tracks the progress and results of a synchronization
    operation for a connector.
    """

    total_items: int = 0
    indexed: int = 0
    skipped: int = 0
    failed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if the sync operation is complete."""
        return self.completed_at is not None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate the duration of the sync operation in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate of the sync operation.

        Success rate is defined as (indexed + skipped) / total_items.
        Skipped items are considered successful since they were processed
        without errors.

        Returns:
            float: Success rate between 0.0 and 1.0.
                   Returns 1.0 if total_items is 0.
        """
        if self.total_items == 0:
            return 1.0

        successful_items = self.indexed + self.skipped
        return successful_items / self.total_items

    def to_dict(self) -> dict:
        """
        Serialize SyncStats to a dictionary.

        Returns:
            dict: Dictionary representation with all fields and computed properties.
                  Datetime objects are serialized to ISO format strings.
        """
        return {
            "total_items": self.total_items,
            "indexed": self.indexed,
            "skipped": self.skipped,
            "failed": self.failed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "is_complete": self.is_complete,
            "success_rate": self.success_rate,
        }
