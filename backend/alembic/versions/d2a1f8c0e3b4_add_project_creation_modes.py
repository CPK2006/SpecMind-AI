"""add project creation modes

Revision ID: d2a1f8c0e3b4
Revises: 9952b30bade0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2a1f8c0e3b4"
down_revision: Union[str, Sequence[str], None] = "9952b30bade0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("creation_mode", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("idea_pitch", sa.Text(), nullable=True),
    )
    op.execute("UPDATE projects SET creation_mode = 'upload' WHERE creation_mode IS NULL")
    op.alter_column("projects", "creation_mode", nullable=False, server_default="upload")


def downgrade() -> None:
    op.drop_column("projects", "idea_pitch")
    op.drop_column("projects", "creation_mode")