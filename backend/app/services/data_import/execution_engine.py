"""
Execution Engine
Handles actual data import to database
"""
from typing import Dict, List, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.engine import Engine
import structlog

logger = structlog.get_logger()


class ExecutionEngine:
    """Executes data import to database"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine: Optional[Engine] = None
        self.logger = logger.bind(component="execution_engine")
    
    def connect(self):
        """Establish database connection"""
        try:
            self.engine = create_engine(self.connection_string)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.logger.info("database_connected")
        except Exception as e:
            self.logger.error("connection_failed", error=str(e))
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            self.logger.info("database_disconnected")
    
    def execute_import(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema: str = "public",
        import_mode: str = "insert",
        batch_size: int = 1000,
        primary_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute data import
        
        Args:
            df: Dataframe to import
            table_name: Target table name
            schema: Target schema
            import_mode: insert, upsert, or truncate_insert
            batch_size: Number of rows per batch
            primary_keys: Primary key columns for upsert mode
            
        Returns:
            Import results
        """
        if not self.engine:
            self.connect()
        
        total_rows = len(df)
        inserted_rows = 0
        updated_rows = 0
        error_rows = 0
        errors = []
        
        try:
            with self.engine.begin() as conn:
                # Truncate if requested
                if import_mode == "truncate_insert":
                    self.logger.info("truncating_table", table=table_name)
                    conn.execute(text(f'TRUNCATE TABLE "{schema}"."{table_name}"'))
                
                # Process in batches
                for i in range(0, total_rows, batch_size):
                    batch = df.iloc[i:i + batch_size]
                    
                    try:
                        if import_mode == "upsert" and primary_keys:
                            result = self._upsert_batch(
                                conn, batch, table_name, schema, primary_keys
                            )
                            inserted_rows += result['inserted']
                            updated_rows += result['updated']
                        else:
                            # Simple insert
                            batch.to_sql(
                                table_name,
                                conn,
                                schema=schema,
                                if_exists='append',
                                index=False,
                                method='multi'
                            )
                            inserted_rows += len(batch)
                        
                        self.logger.info(
                            "batch_imported",
                            batch_num=i // batch_size + 1,
                            rows=len(batch)
                        )
                    
                    except Exception as e:
                        error_rows += len(batch)
                        errors.append({
                            'batch_start': i,
                            'batch_end': i + len(batch),
                            'error': str(e)
                        })
                        self.logger.error(
                            "batch_import_failed",
                            batch_num=i // batch_size + 1,
                            error=str(e)
                        )
                        # Continue with next batch or raise based on config
                        # For now, we'll continue
            
            return {
                'success': error_rows == 0,
                'total_rows': total_rows,
                'inserted_rows': inserted_rows,
                'updated_rows': updated_rows,
                'error_rows': error_rows,
                'errors': errors
            }
        
        except Exception as e:
            self.logger.error("import_failed", error=str(e))
            raise
    
    def _upsert_batch(
        self,
        conn,
        batch: pd.DataFrame,
        table_name: str,
        schema: str,
        primary_keys: List[str]
    ) -> Dict[str, int]:
        """
        Perform upsert (insert or update) operation
        
        This uses PostgreSQL's ON CONFLICT clause
        """
        inserted = 0
        updated = 0
        
        # Get table columns
        columns = batch.columns.tolist()
        
        # Build INSERT ... ON CONFLICT query
        pk_constraint = ', '.join([f'"{pk}"' for pk in primary_keys])
        col_names = ', '.join([f'"{col}"' for col in columns])
        placeholders = ', '.join([f':{col}' for col in columns])
        
        # Update clause for non-PK columns
        update_cols = [col for col in columns if col not in primary_keys]
        update_clause = ', '.join([f'"{col}" = EXCLUDED."{col}"' for col in update_cols])
        
        if update_clause:
            query = f'''
                INSERT INTO "{schema}"."{table_name}" ({col_names})
                VALUES ({placeholders})
                ON CONFLICT ({pk_constraint})
                DO UPDATE SET {update_clause}
            '''
        else:
            # If all columns are PKs, just ignore conflicts
            query = f'''
                INSERT INTO "{schema}"."{table_name}" ({col_names})
                VALUES ({placeholders})
                ON CONFLICT ({pk_constraint})
                DO NOTHING
            '''
        
        # Execute for each row
        for _, row in batch.iterrows():
            try:
                result = conn.execute(text(query), row.to_dict())
                if result.rowcount > 0:
                    inserted += 1
                else:
                    updated += 1
            except Exception as e:
                self.logger.error("row_upsert_failed", error=str(e))
                raise
        
        return {'inserted': inserted, 'updated': updated}
    
    def get_table_schema(
        self,
        table_name: str,
        schema: str = "public"
    ) -> List[Dict[str, Any]]:
        """Get table schema information"""
        if not self.engine:
            self.connect()
        
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=self.engine, schema=schema)
        
        columns = []
        for col in table.columns:
            columns.append({
                'name': col.name,
                'type': str(col.type),
                'nullable': col.nullable,
                'primary_key': col.primary_key,
                'default': str(col.default) if col.default else None,
                'has_default': col.default is not None
            })
        
        return columns
    
    def list_tables(self, schema: str = "public") -> List[str]:
        """List all tables in schema"""
        if not self.engine:
            self.connect()
        
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"schema": schema})
            return [row[0] for row in result]
    
    def list_schemas(self) -> List[str]:
        """List all schemas"""
        if not self.engine:
            self.connect()
        
        query = text("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [row[0] for row in result]
