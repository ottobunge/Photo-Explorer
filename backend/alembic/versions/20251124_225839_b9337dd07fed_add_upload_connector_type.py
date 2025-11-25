"""add_upload_connector_type

Revision ID: b9337dd07fed
Revises: 0003
Create Date: 2025-11-24 22:58:39.870543+00:00

"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9337dd07fed"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'upload' value to ConnectorType enum."""
    from sqlalchemy.dialects import postgresql

    # Ensure connector enums exist (defensive - should have been created in 0001)
    connector_type_enum = postgresql.ENUM(
        "google_photos", "local", name="connectortype", create_type=False
    )
    connector_status_enum = postgresql.ENUM(
        "disconnected", "connected", "syncing", "error", name="connectorstatus", create_type=False
    )

    # Create enums if they don't exist
    connector_type_enum.create(op.get_bind(), checkfirst=True)
    connector_status_enum.create(op.get_bind(), checkfirst=True)

    # Add 'upload' to the connectortype enum
    op.execute("ALTER TYPE connectortype ADD VALUE IF NOT EXISTS 'upload'")


def downgrade() -> None:
    """Remove 'upload' value from ConnectorType enum.

    Note: PostgreSQL does not support removing values from enums.
    This would require creating a new enum type and migrating data.
    For simplicity, we leave the value in the enum on downgrade.
    """
    # PostgreSQL doesn't support removing enum values
    # Would need to recreate the enum type, which is complex
