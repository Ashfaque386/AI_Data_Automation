"""merge_multi_db_heads

Revision ID: 8952d15dfa26
Revises: d99d1568374b, multi_db_upgrade_001
Create Date: 2026-02-13 17:13:24.710021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8952d15dfa26'
down_revision: Union[str, None] = ('d99d1568374b', 'multi_db_upgrade_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
