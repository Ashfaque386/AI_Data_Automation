"""Add computed_columns to datasets table

Revision ID: add_computed_columns
Revises: add_edit_tracking_tables
Create Date: 2026-01-31 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_computed_columns'
down_revision = 'add_edit_tracking_tables'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('datasets', sa.Column('computed_columns', sa.JSON(), nullable=True, server_default='{}'))


def downgrade():
    op.drop_column('datasets', 'computed_columns')
