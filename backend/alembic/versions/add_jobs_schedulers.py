"""add jobs and schedulers tables

Revision ID: add_jobs_schedulers
Revises: add_conn_profiles_connection_profiles
Create Date: 2026-02-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_jobs_schedulers'
down_revision = 'add_conn_profiles'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scheduled_jobs table
    op.create_table(
        'scheduled_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=True),
        sa.Column('target_schema', sa.String(length=100), nullable=True),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('pre_execution_sql', sa.Text(), nullable=True),
        sa.Column('post_execution_sql', sa.Text(), nullable=True),
        sa.Column('retry_policy', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('max_runtime_seconds', sa.Integer(), nullable=False, server_default='3600'),
        sa.Column('failure_threshold', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('notify_on_success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notify_on_failure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notification_emails', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('notification_webhook', sa.String(length=500), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['connection_id'], ['connection_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_scheduled_jobs_job_type', 'scheduled_jobs', ['job_type'])
    op.create_index('ix_scheduled_jobs_is_active', 'scheduled_jobs', ['is_active'])
    op.create_index('ix_scheduled_jobs_next_run_at', 'scheduled_jobs', ['next_run_at'])
    
    # Create job_executions table
    op.create_table(
        'job_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('rows_processed', sa.Integer(), nullable=True),
        sa.Column('rows_affected', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stack_trace', sa.Text(), nullable=True),
        sa.Column('execution_logs', sa.Text(), nullable=True),
        sa.Column('resource_usage', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_retry', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('parent_execution_id', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.String(length=50), nullable=False),
        sa.Column('triggered_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['scheduled_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_execution_id'], ['job_executions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_job_executions_job_id', 'job_executions', ['job_id'])
    op.create_index('ix_job_executions_status', 'job_executions', ['status'])
    op.create_index('ix_job_executions_created_at', 'job_executions', ['created_at'])
    
    # Create job_parameters table
    op.create_table(
        'job_parameters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('mode', sa.String(length=10), nullable=False, server_default='IN'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['scheduled_jobs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_job_parameters_job_id', 'job_parameters', ['job_id'])
    
    # Create backup_configurations table
    op.create_table(
        'backup_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('database_type', sa.String(length=50), nullable=False),
        sa.Column('database_name', sa.String(length=255), nullable=False),
        sa.Column('backup_type', sa.String(length=20), nullable=False),
        sa.Column('compression_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['scheduled_jobs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_backup_configurations_job_id', 'backup_configurations', ['job_id'])


def downgrade() -> None:
    op.drop_index('ix_backup_configurations_job_id', table_name='backup_configurations')
    op.drop_table('backup_configurations')
    
    op.drop_index('ix_job_parameters_job_id', table_name='job_parameters')
    op.drop_table('job_parameters')
    
    op.drop_index('ix_job_executions_created_at', table_name='job_executions')
    op.drop_index('ix_job_executions_status', table_name='job_executions')
    op.drop_index('ix_job_executions_job_id', table_name='job_executions')
    op.drop_table('job_executions')
    
    op.drop_index('ix_scheduled_jobs_next_run_at', table_name='scheduled_jobs')
    op.drop_index('ix_scheduled_jobs_is_active', table_name='scheduled_jobs')
    op.drop_index('ix_scheduled_jobs_job_type', table_name='scheduled_jobs')
    op.drop_table('scheduled_jobs')
