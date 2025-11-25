"""Add performance indexes for common queries.

Revision ID: 0003
Revises: 0002
Create Date: 2025-11-24 18:10:52.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for common query patterns."""
    # Composite index for external photo lookups (external_id, connector_id)
    # This optimizes find_by_external_id queries which filter by both fields
    op.create_index(
        "ix_photos_external_id_connector_id",
        "photos",
        ["external_id", "connector_id"],
        unique=False,
    )

    # Indexes on photo_album association table for faster joins
    # These optimize queries that filter photos by album_id
    op.create_index(
        "ix_photo_album_photo_id",
        "photo_album",
        ["photo_id"],
        unique=False,
    )
    op.create_index(
        "ix_photo_album_album_id",
        "photo_album",
        ["album_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index("ix_photo_album_album_id", table_name="photo_album")
    op.drop_index("ix_photo_album_photo_id", table_name="photo_album")
    op.drop_index("ix_photos_external_id_connector_id", table_name="photos")
