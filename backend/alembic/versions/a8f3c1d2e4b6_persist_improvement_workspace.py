"""persist the combined improvement workspace

Revision ID: a8f3c1d2e4b6
Revises: f4c3d2e1b0a9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f3c1d2e4b6"
down_revision: Union[str, Sequence[str], None] = "f4c3d2e1b0a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("requirements", sa.Column("improvement_report_result", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("requirements", "improvement_report_result")
