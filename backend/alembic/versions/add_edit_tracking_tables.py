"""Add dataset_changes and dataset_locks tables for edit tracking

Revision ID: add_edit_tracking_tables
Revises: 
Create Date: 2026-01-31 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_edit_tracking_tables'
down_revision = None  # Update this to the latest migration ID
branch_labels = None
depends_on = None


def upgrade():
    """Create dataset_changes and dataset_locks tables."""
    
    # Create dataset_changes table
    op.create_table(
        'dataset_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=True),
        sa.Column('column_name', sa.String(length=255), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_committed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for dataset_changes
    op.create_index('ix_dataset_changes_id', 'dataset_changes', ['id'])
    op.create_index('ix_dataset_changes_dataset_id', 'dataset_changes', ['dataset_id'])
    op.create_index('ix_dataset_changes_session_id', 'dataset_changes', ['session_id'])
    op.create_index('ix_dataset_changes_is_committed', 'dataset_changes', ['is_committed'])
    op.create_index('idx_dataset_session', 'dataset_changes', ['dataset_id', 'session_id'])
    op.create_index('idx_session_committed', 'dataset_changes', ['session_id', 'is_committed'])
    op.create_index('idx_dataset_timestamp', 'dataset_changes', ['dataset_id', 'timestamp'])
    
    # Create dataset_locks table
    op.create_table(
        'dataset_locks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dataset_id'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create indexes for dataset_locks
    op.create_index('ix_dataset_locks_id', 'dataset_locks', ['id'])


def downgrade():
    """Drop dataset_changes and dataset_locks tables."""
    
    # Drop indexes first
    op.drop_index('ix_dataset_locks_id', table_name='dataset_locks')
    
    op.drop_index('idx_dataset_timestamp', table_name='dataset_changes')
    op.drop_index('idx_session_committed', table_name='dataset_changes')
    op.drop_index('idx_dataset_session', table_name='dataset_changes')
    op.drop_index('ix_dataset_changes_is_committed', table_name='dataset_changes')
    op.drop_index('ix_dataset_changes_session_id', table_name='dataset_changes')
    op.drop_index('ix_dataset_changes_dataset_id', table_name='dataset_changes')
    op.drop_index('ix_dataset_changes_id', table_name='dataset_changes')
    
    # Drop tables
    op.drop_table('dataset_locks')
    op.drop_table('dataset_changes')
