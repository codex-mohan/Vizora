"""add camera source fields

Revision ID: 002
Revises: 001
Create Date: 2026-06-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cameras", sa.Column("source_type", sa.String(20), nullable=True, server_default="upload"))
    op.add_column("cameras", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("cameras", sa.Column("model_profile", sa.String(20), nullable=False, server_default="fast"))
    op.add_column("cameras", sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("cameras", "enabled")
    op.drop_column("cameras", "model_profile")
    op.drop_column("cameras", "source_url")
    op.drop_column("cameras", "source_type")
