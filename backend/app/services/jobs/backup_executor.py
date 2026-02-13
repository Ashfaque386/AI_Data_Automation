"""
Database Backup Executor
Executes database backups using native tools (pg_dump, mysqldump)
"""
from typing import Dict, Any, List
import subprocess
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import traceback

from app.services.jobs.job_executor_base import JobExecutorBase, ExecutionResult, ValidationResult


class BackupExecutor(JobExecutorBase):
    """Execute database backups"""
    
    def __init__(self, connection_string: str, job_config: Dict[str, Any], storage_path: str = "/app/backups"):
        super().__init__(connection_string, job_config)
        self.storage_path = storage_path
        
        # Ensure storage directory exists
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
    
    def validate_config(self) -> ValidationResult:
        """Validate backup configuration"""
        errors = []
        warnings = []
        
        # Check required fields
        if 'database_type' not in self.job_config:
            errors.append("Missing required field: database_type")
        elif self.job_config['database_type'] not in ['postgresql', 'mysql']:
            errors.append(f"Unsupported database type: {self.job_config['database_type']}")
        
        if 'database_name' not in self.job_config:
            errors.append("Missing required field: database_name")
        
        # Check backup type
        backup_type = self.job_config.get('backup_type', 'full')
        if backup_type not in ['full', 'schema_only', 'data_only']:
            errors.append(f"Invalid backup type: {backup_type}")
        
        # Check storage path is writable
        if not os.access(self.storage_path, os.W_OK):
            errors.append(f"Storage path not writable: {self.storage_path}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def execute(self, execution_id: int) -> ExecutionResult:
        """Execute database backup"""
        self.log("Starting database backup", execution_id=execution_id)
        
        # Validate first
        validation = self.validate_config()
        if not validation.valid:
            return ExecutionResult(
                success=False,
                error_message=f"Validation failed: {', '.join(validation.errors)}",
                execution_logs=self.get_logs()
            )
        
        database_type = self.job_config['database_type']
        database_name = self.job_config['database_name']
        backup_type = self.job_config.get('backup_type', 'full')
        compression = self.job_config.get('compression_enabled', True)
        # Parse connection string to get host/port for logging
        try:
            # Simple parsing for logging purposes
            if 'postgresql://' in self.connection_string:
                clean_conn = self.connection_string.replace('postgresql://', '')
                if '@' in clean_conn:
                    host_part = clean_conn.split('@')[1].split('/')[0]
                    self.log(f"Target: PostgreSQL on {host_part}")
            elif 'mysql' in self.connection_string:
                clean_conn = self.connection_string.split('@')[1].split('/')[0] if '@' in self.connection_string else "unknown"
                self.log(f"Target: MySQL on {clean_conn}")
        except Exception:
            self.log(f"Target: Could not parse host from connection string")

        self.log(f"Database: {database_name}")
        self.log(f"Type: {database_type}")
        self.log(f"Backup type: {backup_type}")
        self.log(f"Compression: {compression}")
        self.log(f"Storage Path: {self.storage_path}")

        
        # Generate backup filename
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{database_name}_{backup_type}_{timestamp}"
        
        format = self.job_config.get('format', 'custom')
        
        if database_type == 'postgresql':
            if format == 'plain':
                backup_filename += '.sql'
            elif format == 'tar':
                backup_filename += '.tar'
            else:
                backup_filename += '.dump'
                
            if compression:
                backup_filename += '.gz'
        elif database_type == 'mysql':
            backup_filename += '.sql' if not compression else '.sql.gz'
        
        backup_path = os.path.join(self.storage_path, backup_filename)
        
        self.log(f"Backup file: {backup_path}")
        
        try:
            # Execute backup based on database type
            if database_type == 'postgresql':
                result = self._backup_postgresql(backup_path, backup_type, compression)
            elif database_type == 'mysql':
                result = self._backup_mysql(backup_path, backup_type, compression)
            else:
                raise ValueError(f"Unsupported database type: {database_type}")
            
            if not result['success']:
                return ExecutionResult(
                    success=False,
                    error_message=result['error'],
                    execution_logs=self.get_logs()
                )
            
            # Calculate file size and checksum
            file_size = os.path.getsize(backup_path)
            checksum = self._calculate_checksum(backup_path)
            
            self.log(f"Backup completed successfully")
            self.log(f"File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
            self.log(f"Checksum (SHA256): {checksum}")
            
            # Calculate expiration date
            retention_days = self.job_config.get('retention_days', 30)
            expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)
            
            return ExecutionResult(
                success=True,
                result_data={
                    'backup_path': backup_path,
                    'backup_filename': backup_filename,
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / 1024 / 1024, 2),
                    'checksum': checksum,
                    'backup_type': backup_type,
                    'compression_enabled': compression,
                    'retention_days': retention_days,
                    'expires_at': expires_at.isoformat()
                },
                execution_logs=self.get_logs()
            )
            
        except Exception as e:
            self.log(f"Backup failed: {str(e)}", level="error")
            
            # Clean up partial backup file
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                    self.log("Cleaned up partial backup file")
                except Exception:
                    pass
            
            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_stack_trace=traceback.format_exc(),
                execution_logs=self.get_logs()
            )
    
    def _backup_postgresql(self, backup_path: str, backup_type: str, compression: bool) -> Dict[str, Any]:
        """Execute PostgreSQL backup using pg_dump"""
        # Parse connection string
        # Format: postgresql://user:password@host:port/database
        parts = self.connection_string.replace('postgresql://', '').split('@')
        if len(parts) != 2:
            return {'success': False, 'error': 'Invalid connection string format'}
        
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host_port = host_port_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        database = host_port_db[1] if len(host_port_db) > 1 else ''
        
        # Determine pg_dump path
        pg_dump_cmd = 'pg_dump'
        if os.path.exists('/app/pg_dump'):
            pg_dump_cmd = '/app/pg_dump'
            self.log(f"Using custom pg_dump: {pg_dump_cmd}")
            
        # Build pg_dump command
        cmd = [pg_dump_cmd]
        cmd.extend(['-h', host])
        cmd.extend(['-p', port])
        cmd.extend(['-U', username])
        cmd.extend(['-d', database])
        format = self.job_config.get('format', 'custom')
        if format == 'plain':
            cmd.extend(['-F', 'p'])
        elif format == 'tar':
            cmd.extend(['-F', 't'])
        else:
            cmd.extend(['-F', 'c'])  # Custom format
        
        # Add backup type options
        if backup_type == 'schema_only':
            cmd.append('--schema-only')
        elif backup_type == 'data_only':
            cmd.append('--data-only')
        
        # Add compression
        if compression:
            cmd.extend(['-Z', '6'])  # Compression level 6
        
        cmd.extend(['-f', backup_path])
        
        self.log(f"Executing: pg_dump (password hidden)")
        
        # Set password in environment
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                self.log(f"pg_dump failed: {error_msg}", level="error")
                return {'success': False, 'error': error_msg}
            
            self.log("pg_dump completed successfully")
            return {'success': True}
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Backup timeout (exceeded 1 hour)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _backup_mysql(self, backup_path: str, backup_type: str, compression: bool) -> Dict[str, Any]:
        """Execute MySQL backup using mysqldump"""
        # Parse connection string
        # Format: mysql+pymysql://user:password@host:port/database
        parts = self.connection_string.replace('mysql+pymysql://', '').split('@')
        if len(parts) != 2:
            return {'success': False, 'error': 'Invalid connection string format'}
        
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host_port = host_port_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '3306'
        database = host_port_db[1] if len(host_port_db) > 1 else ''
        
        # Build mysqldump command
        cmd = ['mysqldump']
        cmd.extend(['-h', host])
        cmd.extend(['-P', port])
        cmd.extend(['-u', username])
        cmd.extend([f'-p{password}'])  # Note: no space after -p
        
        # Add backup type options
        if backup_type == 'schema_only':
            cmd.append('--no-data')
        elif backup_type == 'data_only':
            cmd.append('--no-create-info')
        
        cmd.append(database)
        
        self.log(f"Executing: mysqldump (password hidden)")
        
        try:
            # Execute mysqldump
            with open(backup_path, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600  # 1 hour timeout
                )
            
            if result.returncode != 0:
                error_msg = result.stderr
                self.log(f"mysqldump failed: {error_msg}", level="error")
                return {'success': False, 'error': error_msg}
            
            # Compress if requested
            if compression:
                self.log("Compressing backup file...")
                subprocess.run(['gzip', backup_path], check=True)
                # Update backup_path to include .gz extension
                # Note: This is handled by the caller
            
            self.log("mysqldump completed successfully")
            return {'success': True}
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Backup timeout (exceeded 1 hour)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_required_permissions(self) -> List[str]:
        """Get required permissions"""
        backup_type = self.job_config.get('backup_type', 'full')
        
        if backup_type == 'schema_only':
            return ['SELECT', 'SHOW VIEW']
        elif backup_type == 'data_only':
            return ['SELECT']
        else:  # full
            return ['SELECT', 'SHOW VIEW', 'TRIGGER', 'LOCK TABLES']
