"""initial schema

Revision ID: f4429ea69986
Revises:
Create Date: 2026-02-21 10:42:08.534507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f4429ea69986'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("entries")
    op.drop_table("sessions")
