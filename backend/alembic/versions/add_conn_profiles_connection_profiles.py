"""add_connection_profiles_table

Revision ID: add_conn_profiles
Revises: 
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_conn_profiles'
down_revision = None  # Update this to the latest revision ID
branch_labels = None
depends_on = None


def upgrade():
    # Create connection_profiles table
    op.create_table(
        'connection_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('db_type', sa.String(length=50), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('database', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('encrypted_password', sa.Text(), nullable=True),
        sa.Column('schema', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_read_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_connection_profiles_id'), 'connection_profiles', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_connection_profiles_id'), table_name='connection_profiles')
    op.drop_table('connection_profiles')
