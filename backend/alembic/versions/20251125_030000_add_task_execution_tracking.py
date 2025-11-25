"""add_task_execution_tracking

Add task_executions table for tracking Celery task executions and ensuring idempotency.

This table allows tasks to check if they've already completed successfully before
running again, preventing duplicate processing when tasks are retried.

Revision ID: 8c4d9f2a5b1e
Revises: 0f9f526b61c8
Create Date: 2025-11-25 03:00:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c4d9f2a5b1e"
down_revision: Union[str, None] = "0f9f526b61c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add task_executions table for idempotency tracking."""
    op.create_table(
        "task_executions",
        sa.Column("task_id", sa.String(length=255), nullable=False, primary_key=True),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("task_id"),
    )

    # Add composite index for finding completed tasks by name and completion time
    op.create_index(
        "ix_task_executions_name_status",
        "task_executions",
        ["task_name", "status"],
    )

    # Add index for cleanup queries (finding old completed tasks)
    op.create_index(
        "ix_task_executions_completed_at",
        "task_executions",
        ["completed_at"],
        postgresql_where=sa.text("completed_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove task_executions table."""
    op.drop_index(
        "ix_task_executions_completed_at",
        table_name="task_executions",
    )
    op.drop_index(
        "ix_task_executions_name_status",
        table_name="task_executions",
    )
    op.drop_table("task_executions")
