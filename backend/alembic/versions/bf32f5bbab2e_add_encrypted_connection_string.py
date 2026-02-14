"""add_encrypted_connection_string

Revision ID: bf32f5bbab2e
Revises: be35d24d35c7
Create Date: 2026-02-13 19:21:53.177381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf32f5bbab2e'
down_revision: Union[str, None] = 'be35d24d35c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('connection_profiles', sa.Column('encrypted_connection_string', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('connection_profiles', 'encrypted_connection_string')
