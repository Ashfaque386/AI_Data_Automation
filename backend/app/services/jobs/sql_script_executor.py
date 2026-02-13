"""
SQL Script Executor
Executes SQL scripts with validation and transaction control
"""
from typing import Dict, Any, List
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import traceback
import re

from app.services.jobs.job_executor_base import JobExecutorBase, ExecutionResult, ValidationResult


class SQLScriptExecutor(JobExecutorBase):
    """Execute SQL scripts"""
    
    def validate_config(self) -> ValidationResult:
        """Validate SQL script configuration"""
        errors = []
        warnings = []
        
        # Check required fields
        if 'sql_script' not in self.job_config:
            errors.append("Missing required field: sql_script")
        elif not self.job_config['sql_script'].strip():
            errors.append("SQL script cannot be empty")
        
        # Check for potentially dangerous operations
        sql_script = self.job_config.get('sql_script', '').upper()
        dangerous_keywords = ['DROP DATABASE', 'DROP SCHEMA', 'TRUNCATE TABLE']
        for keyword in dangerous_keywords:
            if keyword in sql_script:
                warnings.append(f"Potentially dangerous operation detected: {keyword}")
        
        # Validate read-only mode if specified
        read_only = self.job_config.get('read_only', False)
        if read_only:
            write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE']
            for keyword in write_keywords:
                if re.search(rf'\b{keyword}\b', sql_script):
                    errors.append(f"Write operation '{keyword}' not allowed in read-only mode")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def execute(self, execution_id: int) -> ExecutionResult:
        """Execute SQL script"""
        self.log("Starting SQL script execution", execution_id=execution_id)
        
        # Validate first
        validation = self.validate_config()
        if not validation.valid:
            return ExecutionResult(
                success=False,
                error_message=f"Validation failed: {', '.join(validation.errors)}",
                execution_logs=self.get_logs()
            )
        
        sql_script = self.job_config['sql_script']
        read_only = self.job_config.get('read_only', False)
        use_transaction = self.job_config.get('use_transaction', True)
        
        self.log(f"SQL script length: {len(sql_script)} characters")
        self.log(f"Read-only mode: {read_only}")
        self.log(f"Transaction mode: {use_transaction}")
        
        engine = None
        connection = None
        transaction = None
        
        try:
            # Create engine
            engine = create_engine(self.connection_string, pool_pre_ping=True)
            connection = engine.connect()
            
            self.log("Database connection established")
            
            # Start transaction if requested
            if use_transaction:
                transaction = connection.begin()
                self.log("Transaction started")
            
            # Execute script
            result_proxy = connection.execute(text(sql_script))
            
            rows_affected = result_proxy.rowcount if result_proxy.rowcount >= 0 else 0
            self.log(f"Script executed successfully, rows affected: {rows_affected}")
            
            # Try to fetch results if it's a SELECT query
            result_data = None
            try:
                if result_proxy.returns_rows:
                    rows = result_proxy.fetchall()
                    columns = list(result_proxy.keys())
                    result_data = {
                        'columns': columns,
                        'rows': [dict(zip(columns, row)) for row in rows[:100]],  # Limit to 100 rows
                        'total_rows': len(rows)
                    }
                    self.log(f"Query returned {len(rows)} rows")
            except Exception:
                pass  # Not a SELECT query
            
            # Commit transaction if active
            if transaction:
                transaction.commit()
                self.log("Transaction committed")
            
            return ExecutionResult(
                success=True,
                rows_affected=rows_affected,
                result_data=result_data,
                execution_logs=self.get_logs()
            )
            
        except SQLAlchemyError as e:
            self.log(f"SQL execution error: {str(e)}", level="error")
            
            # Rollback transaction if active
            if transaction:
                try:
                    transaction.rollback()
                    self.log("Transaction rolled back")
                except Exception:
                    pass
            
            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_stack_trace=traceback.format_exc(),
                execution_logs=self.get_logs()
            )
            
        except Exception as e:
            self.log(f"Unexpected error: {str(e)}", level="error")
            
            if transaction:
                try:
                    transaction.rollback()
                except Exception:
                    pass
            
            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_stack_trace=traceback.format_exc(),
                execution_logs=self.get_logs()
            )
            
        finally:
            # Cleanup
            if connection:
                connection.close()
                self.log("Database connection closed")
            if engine:
                engine.dispose()
    
    def get_required_permissions(self) -> List[str]:
        """Get required permissions based on SQL script"""
        sql_script = self.job_config.get('sql_script', '').upper()
        permissions = set()
        
        if any(keyword in sql_script for keyword in ['SELECT', 'WITH']):
            permissions.add('SELECT')
        if 'INSERT' in sql_script:
            permissions.add('INSERT')
        if 'UPDATE' in sql_script:
            permissions.add('UPDATE')
        if 'DELETE' in sql_script:
            permissions.add('DELETE')
        if any(keyword in sql_script for keyword in ['CREATE', 'ALTER', 'DROP']):
            permissions.add('DDL')
        
        return list(permissions)
