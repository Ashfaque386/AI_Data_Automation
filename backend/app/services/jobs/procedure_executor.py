"""
Stored Procedure Executor
Executes stored procedures and functions with parameter handling
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import traceback

from app.services.jobs.job_executor_base import JobExecutorBase, ExecutionResult, ValidationResult


class ProcedureExecutor(JobExecutorBase):
    """Execute stored procedures and functions"""
    
    def validate_config(self) -> ValidationResult:
        """Validate procedure configuration"""
        errors = []
        warnings = []
        
        # Check required fields
        if 'procedure_name' not in self.job_config:
            errors.append("Missing required field: procedure_name")
        
        if 'schema' not in self.job_config:
            warnings.append("Schema not specified, using default schema")
        
        # Validate parameters if provided
        parameters = self.job_config.get('parameters', [])
        if not isinstance(parameters, list):
            errors.append("Parameters must be a list")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def execute(self, execution_id: int) -> ExecutionResult:
        """Execute stored procedure"""
        self.log("Starting stored procedure execution", execution_id=execution_id)
        
        # Validate first
        validation = self.validate_config()
        if not validation.valid:
            return ExecutionResult(
                success=False,
                error_message=f"Validation failed: {', '.join(validation.errors)}",
                execution_logs=self.get_logs()
            )
        
        procedure_name = self.job_config['procedure_name']
        schema = self.job_config.get('schema', 'public')
        parameters = self.job_config.get('parameters', [])
        
        self.log(f"Procedure: {schema}.{procedure_name}")
        self.log(f"Parameters: {self._sanitize_for_logging(parameters)}")
        
        engine = None
        connection = None
        
        try:
            # Create engine
            engine = create_engine(self.connection_string, pool_pre_ping=True)
            connection = engine.connect()
            
            self.log("Database connection established")
            
            # Build procedure call
            param_placeholders = ', '.join([f':param{i}' for i in range(len(parameters))])
            
            # Determine if it's a function (returns value) or procedure
            is_function = self.job_config.get('is_function', False)
            
            if is_function:
                # For functions, use SELECT
                sql = f"SELECT {schema}.{procedure_name}({param_placeholders})"
            else:
                # For procedures, use CALL
                sql = f"CALL {schema}.{procedure_name}({param_placeholders})"
            
            self.log(f"Executing: {sql}")
            
            # Prepare parameters dict
            params_dict = {f'param{i}': param['value'] for i, param in enumerate(parameters)}
            
            # Execute procedure
            result_proxy = connection.execute(text(sql), params_dict)
            
            self.log("Procedure executed successfully")
            
            # Fetch results
            result_data = None
            rows_processed = 0
            
            try:
                if result_proxy.returns_rows:
                    rows = result_proxy.fetchall()
                    rows_processed = len(rows)
                    
                    if rows:
                        columns = list(result_proxy.keys())
                        result_data = {
                            'columns': columns,
                            'rows': [dict(zip(columns, row)) for row in rows[:100]],  # Limit to 100 rows
                            'total_rows': len(rows)
                        }
                        self.log(f"Procedure returned {len(rows)} rows")
                    else:
                        result_data = {'message': 'Procedure executed successfully, no rows returned'}
            except Exception:
                result_data = {'message': 'Procedure executed successfully'}
            
            return ExecutionResult(
                success=True,
                rows_processed=rows_processed,
                result_data=result_data,
                execution_logs=self.get_logs()
            )
            
        except SQLAlchemyError as e:
            self.log(f"Procedure execution error: {str(e)}", level="error")
            
            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_stack_trace=traceback.format_exc(),
                execution_logs=self.get_logs()
            )
            
        except Exception as e:
            self.log(f"Unexpected error: {str(e)}", level="error")
            
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
        """Get required permissions"""
        return ['EXECUTE']
    
    @staticmethod
    def discover_procedures(connection_string: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Discover stored procedures and functions in a schema
        
        Args:
            connection_string: Database connection string
            schema: Schema name
            
        Returns:
            List of procedure/function definitions
        """
        engine = create_engine(connection_string, pool_pre_ping=True)
        
        try:
            with engine.connect() as connection:
                # Query for PostgreSQL routines
                query = text("""
                    SELECT 
                        routine_name,
                        routine_type,
                        data_type as return_type,
                        routine_definition
                    FROM information_schema.routines
                    WHERE routine_schema = :schema
                    ORDER BY routine_name
                """)
                
                result = connection.execute(query, {'schema': schema})
                procedures = []
                
                for row in result:
                    procedures.append({
                        'name': row[0],
                        'type': row[1],  # FUNCTION or PROCEDURE
                        'return_type': row[2],
                        'definition': row[3]
                    })
                
                return procedures
                
        finally:
            engine.dispose()
    
    @staticmethod
    def get_procedure_parameters(connection_string: str, procedure_name: str, schema: str = 'public') -> List[Dict[str, Any]]:
        """
        Get parameters for a specific procedure/function
        
        Args:
            connection_string: Database connection string
            procedure_name: Name of the procedure/function
            schema: Schema name
            
        Returns:
            List of parameter definitions
        """
        engine = create_engine(connection_string, pool_pre_ping=True)
        
        try:
            with engine.connect() as connection:
                # Query for PostgreSQL routine parameters
                query = text("""
                    SELECT 
                        parameter_name,
                        data_type,
                        parameter_mode,
                        ordinal_position
                    FROM information_schema.parameters
                    WHERE specific_schema = :schema
                    AND specific_name = :procedure_name
                    ORDER BY ordinal_position
                """)
                
                result = connection.execute(query, {
                    'schema': schema,
                    'procedure_name': procedure_name
                })
                
                parameters = []
                for row in result:
                    parameters.append({
                        'name': row[0],
                        'type': row[1],
                        'mode': row[2],  # IN, OUT, INOUT
                        'position': row[3]
                    })
                
                return parameters
                
        finally:
            engine.dispose()
