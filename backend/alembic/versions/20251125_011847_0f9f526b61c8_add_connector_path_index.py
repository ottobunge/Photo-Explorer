"""add_connector_path_index

Add database index on config->>'path' for connectors table.

This partial index improves performance of find_by_path() queries
by indexing the JSON path field for local connectors. The index
only includes rows where the path field is not null, reducing
index size and maintenance overhead.

Revision ID: 0f9f526b61c8
Revises: b9337dd07fed
Create Date: 2025-11-25 01:18:47.718098+00:00

"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f9f526b61c8"
down_revision: Union[str, None] = "b9337dd07fed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add partial index on config->>'path' for connectors table.

    This index optimizes queries that search for connectors by their
    filesystem path. It's a partial index that only includes rows where
    the path field exists in the config JSON, which reduces index size
    and is more efficient than indexing all rows.
    """
    op.execute(
        """
        CREATE INDEX ix_connectors_config_path
        ON connectors
        USING btree ((config->>'path'))
        WHERE config->>'path' IS NOT NULL
    """
    )


def downgrade() -> None:
    """Remove the connector path index."""
    op.execute("DROP INDEX IF EXISTS ix_connectors_config_path")
