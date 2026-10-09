"""store refactoring and clarification results

Revision ID: f4c3d2e1b0a9
Revises: e3b2c1d4f5a6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c3d2e1b0a9"
down_revision: Union[str, Sequence[str], None] = "e3b2c1d4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("requirements", sa.Column("refactored_srs_result", sa.Text(), nullable=True))
    op.add_column("requirements", sa.Column("clarification_questions_result", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("requirements", "clarification_questions_result")
    op.drop_column("requirements", "refactored_srs_result")