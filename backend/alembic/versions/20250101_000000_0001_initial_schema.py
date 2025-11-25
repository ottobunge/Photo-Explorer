"""Initial database schema.

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create connector type and status enums
    connector_type_enum = postgresql.ENUM(
        "google_photos", "local", name="connectortype", create_type=False
    )
    connector_status_enum = postgresql.ENUM(
        "disconnected", "connected", "syncing", "error", name="connectorstatus", create_type=False
    )

    # Create enums in database
    connector_type_enum.create(op.get_bind(), checkfirst=True)
    connector_status_enum.create(op.get_bind(), checkfirst=True)

    # Create connectors table
    op.create_table(
        "connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("google_photos", "local", name="connectortype", create_type=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "disconnected",
                "connected",
                "syncing",
                "error",
                name="connectorstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="disconnected",
        ),
        sa.Column("config", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("last_sync_stats", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create face_clusters table
    op.create_table(
        "face_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("representative_face_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_face_clusters_name"), "face_clusters", ["name"], unique=False)

    # Create albums table
    op.create_table(
        "albums",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("cover_photo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create photos table
    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        # Connector reference
        sa.Column("connector_type", sa.String(50), nullable=False, server_default="local"),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("source_path", sa.String(1024), nullable=True),
        sa.Column("source_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        # Storage paths
        sa.Column("storage_path", sa.String(1024), nullable=True),
        sa.Column("thumbnail_path", sa.String(1024), nullable=True),
        sa.Column("cached_thumbnail_path", sa.String(1024), nullable=True),
        sa.Column("thumbnail_expires_at", sa.DateTime(), nullable=True),
        # Legacy
        sa.Column("original_path", sa.String(1024), nullable=True),
        # Metadata
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("taken_at", sa.DateTime(), nullable=True),
        sa.Column("exif_data", postgresql.JSON(), nullable=True),
        # AI-generated content
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("scene_type", sa.String(100), nullable=True),
        sa.Column("scene_confidence", sa.Float(), nullable=True),
        sa.Column("is_indoor", sa.Boolean(), nullable=True),
        sa.Column("detected_objects", postgresql.JSON(), nullable=True),
        # Processing status
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="pending"),
        # Foreign keys
        sa.ForeignKeyConstraint(["connector_id"], ["connectors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        comment="Photos table with connector support",
    )
    op.create_index(op.f("ix_photos_external_id"), "photos", ["external_id"], unique=False)
    op.create_index(op.f("ix_photos_taken_at"), "photos", ["taken_at"], unique=False)
    op.create_index(
        op.f("ix_photos_processing_status"), "photos", ["processing_status"], unique=False
    )

    # Add foreign key for album cover_photo_id (now that photos exists)
    op.create_foreign_key(
        "fk_albums_cover_photo_id",
        "albums",
        "photos",
        ["cover_photo_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create faces table
    op.create_table(
        "faces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Bounding box
        sa.Column("bbox_x", sa.Float(), nullable=False),
        sa.Column("bbox_y", sa.Float(), nullable=False),
        sa.Column("bbox_width", sa.Float(), nullable=False),
        sa.Column("bbox_height", sa.Float(), nullable=False),
        # Storage
        sa.Column("crop_path", sa.String(1024), nullable=True),
        # Quality metrics
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("detection_confidence", sa.Float(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        # Foreign keys
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["face_clusters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_faces_photo_id"), "faces", ["photo_id"], unique=False)
    op.create_index(op.f("ix_faces_cluster_id"), "faces", ["cluster_id"], unique=False)

    # Create photo_album association table
    op.create_table(
        "photo_album",
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("album_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("photo_id", "album_id"),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("photo_album")
    op.drop_table("faces")
    op.drop_constraint("fk_albums_cover_photo_id", "albums", type_="foreignkey")
    op.drop_table("photos")
    op.drop_table("albums")
    op.drop_table("face_clusters")
    op.drop_table("connectors")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS connectorstatus")
    op.execute("DROP TYPE IF EXISTS connectortype")
