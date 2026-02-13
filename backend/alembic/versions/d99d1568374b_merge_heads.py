"""merge_heads

Revision ID: d99d1568374b
Revises: add_computed_columns, add_jobs_schedulers
Create Date: 2026-02-08 13:13:56.479890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd99d1568374b'
down_revision: Union[str, None] = ('add_computed_columns', 'add_jobs_schedulers')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
