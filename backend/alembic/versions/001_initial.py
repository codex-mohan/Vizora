"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.Enum("admin", "reviewer", "viewer", name="user_role"), server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location_name", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("current_mode", sa.String(20), server_default="CLEAN"),
        sa.Column("status", sa.String(20), server_default="online"),
        sa.Column("scene_config", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id"), nullable=True),
        sa.Column("violation_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("review_required", sa.Boolean(), server_default="false"),
        sa.Column("review_reasons", postgresql.JSON(), nullable=True),
        sa.Column("vehicle_class", sa.String(50), nullable=True),
        sa.Column("plate_text", sa.String(50), nullable=True),
        sa.Column("plate_hash", sa.String(64), nullable=True),
        sa.Column("location_name", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_table(
        "evidence_packets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("violation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("violations.id"), nullable=False),
        sa.Column("frame_urls", postgresql.JSON(), nullable=False),
        sa.Column("plate_crop_url", sa.String(500), nullable=True),
        sa.Column("annotated_frame_url", sa.String(500), nullable=True),
        sa.Column("vlm_description", sa.Text(), nullable=True),
        sa.Column("hash_chain", sa.String(64), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "plates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("plate_text", sa.String(50), nullable=False),
        sa.Column("plate_hash", sa.String(64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("violation_count", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "processing_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id"), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("violation_count", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_violations_violation_type", "violations", ["violation_type"])
    op.create_index("ix_violations_created_at", "violations", ["created_at"])
    op.create_index("ix_violations_camera_id", "violations", ["camera_id"])
    op.create_index("ix_violations_plate_hash", "violations", ["plate_hash"])
    op.create_index("ix_plates_plate_hash", "plates", ["plate_hash"])
    op.create_index("ix_processing_logs_request_id", "processing_logs", ["request_id"])
    op.create_index("ix_processing_logs_created_at", "processing_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_processing_logs_created_at", table_name="processing_logs")
    op.drop_index("ix_processing_logs_request_id", table_name="processing_logs")
    op.drop_index("ix_plates_plate_hash", table_name="plates")
    op.drop_index("ix_violations_plate_hash", table_name="violations")
    op.drop_index("ix_violations_camera_id", table_name="violations")
    op.drop_index("ix_violations_created_at", table_name="violations")
    op.drop_index("ix_violations_violation_type", table_name="violations")
    op.drop_table("processing_logs")
    op.drop_table("plates")
    op.drop_table("evidence_packets")
    op.drop_table("violations")
    op.drop_table("cameras")
    op.drop_table("users")
    op.drop_table("organizations")
    op.execute("DROP TYPE IF EXISTS user_role")
