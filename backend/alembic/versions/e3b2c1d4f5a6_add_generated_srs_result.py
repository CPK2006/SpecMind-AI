"""store generated pitch SRS

Revision ID: e3b2c1d4f5a6
Revises: d2a1f8c0e3b4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3b2c1d4f5a6"
down_revision: Union[str, Sequence[str], None] = "d2a1f8c0e3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("generated_srs_result", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "generated_srs_result")