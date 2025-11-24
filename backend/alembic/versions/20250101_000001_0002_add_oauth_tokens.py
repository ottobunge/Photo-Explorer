"""Add oauth_tokens table.

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-01 00:00:01.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create oauth_tokens table."""
    op.create_table(
        "oauth_tokens",
        sa.Column("connector_type", sa.String(50), primary_key=True),
        sa.Column("encrypted_data", sa.String(4096), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop oauth_tokens table."""
    op.drop_table("oauth_tokens")
