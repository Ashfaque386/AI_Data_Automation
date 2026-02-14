"""multi_database_connection_manager

Revision ID: multi_db_upgrade_001
Revises: add_jobs_schedulers
Create Date: 2026-02-13 22:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'multi_db_upgrade_001'
down_revision = 'add_jobs_schedulers'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    connection_type_enum = postgresql.ENUM(
        'postgresql', 'mysql', 'mariadb', 'oracle', 'sqlserver', 'sqlite', 'mongodb',
        name='connectiontype'
    )
    connection_group_enum = postgresql.ENUM(
        'production', 'staging', 'development', 'analytics', 'testing',
        name='connectiongroup'
    )
    connection_mode_enum = postgresql.ENUM(
        'read_write', 'read_only', 'maintenance',
        name='connectionmode'
    )
    health_status_enum = postgresql.ENUM(
        'online', 'offline', 'degraded', 'unknown',
        name='healthstatus'
    )
    
    connection_type_enum.create(op.get_bind())
    connection_group_enum.create(op.get_bind())
    connection_mode_enum.create(op.get_bind())
    health_status_enum.create(op.get_bind())
    
    # Alter connection_profiles table
    # 1. Add new columns
    op.add_column('connection_profiles', sa.Column('connection_group', sa.Enum('production', 'staging', 'development', 'analytics', 'testing', name='connectiongroup'), nullable=True))
    op.add_column('connection_profiles', sa.Column('connection_mode', sa.Enum('read_write', 'read_only', 'maintenance', name='connectionmode'), nullable=True))
    op.add_column('connection_profiles', sa.Column('ssl_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('connection_profiles', sa.Column('ssl_cert_path', sa.String(length=500), nullable=True))
    op.add_column('connection_profiles', sa.Column('ssl_key_path', sa.String(length=500), nullable=True))
    op.add_column('connection_profiles', sa.Column('ssl_ca_path', sa.String(length=500), nullable=True))
    op.add_column('connection_profiles', sa.Column('pool_size', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('connection_profiles', sa.Column('max_connections', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('connection_profiles', sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'))
    op.add_column('connection_profiles', sa.Column('health_status', sa.Enum('online', 'offline', 'degraded', 'unknown', name='healthstatus'), nullable=True))
    op.add_column('connection_profiles', sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True))
    op.add_column('connection_profiles', sa.Column('response_time_ms', sa.Integer(), nullable=True))
    op.add_column('connection_profiles', sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connection_profiles', sa.Column('capabilities', sa.JSON(), nullable=True))
    op.add_column('connection_profiles', sa.Column('db_metadata', sa.JSON(), nullable=True))
    op.add_column('connection_profiles', sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'))
    
    # 2. Set default values for existing rows
    op.execute("UPDATE connection_profiles SET connection_group = 'development' WHERE connection_group IS NULL")
    op.execute("UPDATE connection_profiles SET connection_mode = 'read_write' WHERE connection_mode IS NULL")
    op.execute("UPDATE connection_profiles SET health_status = 'unknown' WHERE health_status IS NULL")
    op.execute("UPDATE connection_profiles SET schema = 'public' WHERE schema IS NULL")
    
    # 3. Make columns non-nullable after setting defaults
    op.alter_column('connection_profiles', 'connection_group', nullable=False)
    op.alter_column('connection_profiles', 'connection_mode', nullable=False)
    op.alter_column('connection_profiles', 'health_status', nullable=False)
    
    # 4. Convert db_type to enum
    op.execute("ALTER TABLE connection_profiles ALTER COLUMN db_type TYPE connectiontype USING db_type::connectiontype")
    
    # Create connection_health_logs table
    op.create_table(
        'connection_health_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('checked_by', sa.String(length=50), nullable=False, server_default='system'),
        sa.ForeignKeyConstraint(['connection_id'], ['connection_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_connection_health_logs_connection_id', 'connection_health_logs', ['connection_id'])
    op.create_index('ix_connection_health_logs_timestamp', 'connection_health_logs', ['timestamp'])
    
    # Create connection_permissions table
    op.create_table(
        'connection_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('can_read', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_write', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_execute_ddl', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allowed_schemas', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('denied_tables', postgresql.ARRAY(sa.String()), nullable=True),
        sa.ForeignKeyConstraint(['connection_id'], ['connection_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_connection_permissions_connection_id', 'connection_permissions', ['connection_id'])
    op.create_index('ix_connection_permissions_user_id', 'connection_permissions', ['user_id'])
    op.create_index('ix_connection_permissions_role_id', 'connection_permissions', ['role_id'])


def downgrade():
    # Drop tables
    op.drop_index('ix_connection_permissions_role_id', table_name='connection_permissions')
    op.drop_index('ix_connection_permissions_user_id', table_name='connection_permissions')
    op.drop_index('ix_connection_permissions_connection_id', table_name='connection_permissions')
    op.drop_table('connection_permissions')
    
    op.drop_index('ix_connection_health_logs_timestamp', table_name='connection_health_logs')
    op.drop_index('ix_connection_health_logs_connection_id', table_name='connection_health_logs')
    op.drop_table('connection_health_logs')
    
    # Remove columns from connection_profiles
    op.drop_column('connection_profiles', 'is_default')
    op.drop_column('connection_profiles', 'db_metadata')
    op.drop_column('connection_profiles', 'capabilities')
    op.drop_column('connection_profiles', 'failed_attempts')
    op.drop_column('connection_profiles', 'response_time_ms')
    op.drop_column('connection_profiles', 'last_health_check')
    op.drop_column('connection_profiles', 'health_status')
    op.drop_column('connection_profiles', 'timeout_seconds')
    op.drop_column('connection_profiles', 'max_connections')
    op.drop_column('connection_profiles', 'pool_size')
    op.drop_column('connection_profiles', 'ssl_ca_path')
    op.drop_column('connection_profiles', 'ssl_key_path')
    op.drop_column('connection_profiles', 'ssl_cert_path')
    op.drop_column('connection_profiles', 'ssl_enabled')
    op.drop_column('connection_profiles', 'connection_mode')
    op.drop_column('connection_profiles', 'connection_group')
    
    # Revert db_type to string
    op.execute("ALTER TABLE connection_profiles ALTER COLUMN db_type TYPE VARCHAR(50)")
    
    # Drop enum types
    op.execute("DROP TYPE healthstatus")
    op.execute("DROP TYPE connectionmode")
    op.execute("DROP TYPE connectiongroup")
    op.execute("DROP TYPE connectiontype")
