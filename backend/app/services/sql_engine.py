"""
SQL Execution Engine - DuckDB-Based Query Processing
"""
import time
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd

from app.database import get_duckdb, DuckDBManager
from app.schemas import (
    SQLRequest, SQLResult, SQLResultColumn, QueryType,
    QueryPlan, QueryExplainResult,
    NoCodeQueryRequest, NoCodeJoin, NoCodeFilter, NoCodeAggregation
)
from app.models import Dataset
from sqlalchemy.orm import Session
import structlog

logger = structlog.get_logger()


class SQLEngineError(Exception):
    """SQL engine execution error."""
    pass


class QueryValidator:
    """Validate and classify SQL queries."""
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'\b(DROP|TRUNCATE|ALTER)\s+TABLE\b',
        r'\bDROP\s+DATABASE\b',
        r'\bCREATE\s+DATABASE\b',
        r'\bEXEC(UTE)?\s*\(',
        r';\s*--',  # SQL injection pattern
    ]
    
    # Query type detection
    QUERY_TYPE_PATTERNS = {
        QueryType.SELECT: r'^\s*SELECT\b',
        QueryType.INSERT: r'^\s*INSERT\b',
        QueryType.UPDATE: r'^\s*UPDATE\b',
        QueryType.DELETE: r'^\s*DELETE\b',
        QueryType.DDL: r'^\s*(CREATE|ALTER|DROP)\b',
    }
    
    @classmethod
    def validate(cls, query: str) -> Tuple[bool, str]:
        """
        Validate query for safety.
        
        Returns:
            (is_valid, error_message)
        """
        query_upper = query.upper()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"Dangerous SQL pattern detected"
        
        return True, ""
    
    @classmethod
    def get_query_type(cls, query: str) -> QueryType:
        """Determine the type of SQL query."""
        query_stripped = query.strip()
        
        for qtype, pattern in cls.QUERY_TYPE_PATTERNS.items():
            if re.match(pattern, query_stripped, re.IGNORECASE):
                return qtype
        
        return QueryType.SELECT  # Default to SELECT


class NoCodeQueryBuilder:
    """Build SQL from no-code query configuration."""
    
    OPERATOR_MAP = {
        'eq': '=',
        'neq': '!=',
        'gt': '>',
        'gte': '>=',
        'lt': '<',
        'lte': '<=',
        'like': 'LIKE',
        'in': 'IN',
        'notnull': 'IS NOT NULL',
        'isnull': 'IS NULL'
    }
    
    @classmethod
    def build_query(cls, request: NoCodeQueryRequest) -> str:
        """Build SQL query from no-code request."""
        # SELECT clause
        if request.aggregations:
            select_parts = []
            for agg in request.aggregations:
                if agg.function == 'distinct_count':
                    select_parts.append(f"COUNT(DISTINCT {agg.column}) AS {agg.column}_{agg.function}")
                else:
                    select_parts.append(f"{agg.function.upper()}({agg.column}) AS {agg.column}_{agg.function}")
            
            # Add group by columns to select
            for col in request.group_by:
                if col not in [p.split(' AS ')[0] for p in select_parts]:
                    select_parts.insert(0, col)
            
            select_clause = ", ".join(select_parts)
        else:
            select_clause = ", ".join(request.columns) if request.columns else "*"
        
        # FROM clause
        from_clause = request.datasets[0]
        
        # JOIN clauses
        for join in request.joins:
            join_type = join.join_type.upper()
            from_clause += f" {join_type} JOIN {join.right_dataset} ON {join.left_dataset}.{join.left_column} = {join.right_dataset}.{join.right_column}"
        
        # WHERE clause
        where_conditions = []
        for filter in request.filters:
            op = cls.OPERATOR_MAP.get(filter.operator, '=')
            
            if filter.operator in ['notnull', 'isnull']:
                where_conditions.append(f"{filter.column} {op}")
            elif filter.operator == 'in':
                if isinstance(filter.value, list):
                    values = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in filter.value)
                    where_conditions.append(f"{filter.column} IN ({values})")
                else:
                    where_conditions.append(f"{filter.column} IN ({filter.value})")
            elif filter.operator == 'like':
                where_conditions.append(f"{filter.column} LIKE '{filter.value}'")
            else:
                if isinstance(filter.value, str):
                    where_conditions.append(f"{filter.column} {op} '{filter.value}'")
                else:
                    where_conditions.append(f"{filter.column} {op} {filter.value}")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        
        # GROUP BY clause
        group_by_clause = ", ".join(request.group_by) if request.group_by else ""
        
        # ORDER BY clause
        order_by_clause = ""
        if request.order_by:
            order_by_clause = f"{request.order_by} {'DESC' if request.order_desc else 'ASC'}"
        
        # Build final query
        query = f"SELECT {select_clause} FROM {from_clause}"
        if where_clause:
            query += f" WHERE {where_clause}"
        if group_by_clause:
            query += f" GROUP BY {group_by_clause}"
        if order_by_clause:
            query += f" ORDER BY {order_by_clause}"
        if request.limit:
            query += f" LIMIT {request.limit}"
        
        return query


class SQLEngine:
    """SQL execution engine using DuckDB."""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.duckdb = get_duckdb()
    
    def execute(
        self,
        query: str,
        limit: int = 1000,
        timeout_seconds: int = 30,
        source: str = 'duckdb'
    ) -> SQLResult:
        """
        Execute SQL query and return results.
        
        Args:
            query: SQL query string
            limit: Maximum rows to return
            timeout_seconds: Query timeout
            source: Execution engine ('duckdb' or 'postgres')
            
        Returns:
            SQLResult with data and metadata
        """
        start_time = time.time()
        
        # Validate query
        is_valid, error_msg = QueryValidator.validate(query)
        if not is_valid:
            return SQLResult(
                success=False,
                query=query,
                query_type=QueryType.SELECT,
                execution_time_ms=0,
                error_message=error_msg
            )
        
        query_type = QueryValidator.get_query_type(query)
        
        if source == 'postgres':
            return self._execute_postgres(query, query_type, limit, start_time)
        else:
            return self._execute_duckdb(query, query_type, limit, start_time)

    def _execute_postgres(self, query: str, query_type: QueryType, limit: int, start_time: float) -> SQLResult:
        """Execute query against PostgreSQL."""
        from sqlalchemy import text
        
        try:
            # Add limit if SELECT and no limit present
            execution_query = query
            if query_type == QueryType.SELECT and 'LIMIT' not in query.upper():
                execution_query = f"{query} LIMIT {limit}"
            
            # Use engine connection to avoid interfering with session state
            with self.db.get_bind().connect() as conn:
                result = conn.execute(text(execution_query))
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                if query_type == QueryType.SELECT and result.returns_rows:
                    # Get columns
                    keys = result.keys()
                    columns = [
                        SQLResultColumn(name=key, data_type="unknown") 
                        for key in keys
                    ]
                    
                    # Fetch data
                    rows = result.fetchall()
                    data = [dict(zip(keys, row)) for row in rows]
                    
                    # Try to infer types from first row if available
                    # (SQLAlchemy cursor description extraction is driver-dependent and complex)
                    
                    return SQLResult(
                        success=True,
                        query=query,
                        query_type=query_type,
                        columns=columns,
                        data=data,
                        row_count=len(data),
                        execution_time_ms=execution_time_ms
                    )
                else:
                    # Non-SELECT
                    conn.commit()
                    return SQLResult(
                        success=True,
                        query=query,
                        query_type=query_type,
                        rows_affected=result.rowcount,
                        execution_time_ms=execution_time_ms
                    )
                    
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error("postgres_execution_error", query=query[:200], error=str(e))
            return SQLResult(
                success=False,
                query=query,
                query_type=query_type,
                execution_time_ms=execution_time_ms,
                error_message=str(e)
            )

    def _execute_duckdb(self, query: str, query_type: QueryType, limit: int, start_time: float) -> SQLResult:
        """Execute query against DuckDB."""
        try:
            # Add limit if SELECT and no limit present
            execution_query = query
            if query_type == QueryType.SELECT and 'LIMIT' not in query.upper():
                execution_query = f"{query} LIMIT {limit}"
            
            # Execute query
            result = self.duckdb.execute(execution_query)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            if query_type == QueryType.SELECT:
                # Fetch results
                df = result.df()
                
                # Build column info
                columns = [
                    SQLResultColumn(
                        name=str(col),
                        data_type=str(df[col].dtype)
                    )
                    for col in df.columns
                ]
                
                # Convert to records - handle NaN/Inf for JSON serialization
                # Use numpy to replace all NaN/Inf values with None
                import numpy as np
                import json
                
                logger.info("dataframe_shape", rows=len(df), cols=len(df.columns))
                
                # Replace Inf with NaN first
                df = df.replace([np.inf, -np.inf], np.nan)
                
                # Convert to dict and manually clean each value
                data = []
                for idx, record in enumerate(df.to_dict(orient='records')):
                    cleaned_record = {}
                    for key, value in record.items():
                        # Check for problematic float values
                        if isinstance(value, (float, np.floating)):
                            if np.isnan(value) or np.isinf(value):
                                cleaned_record[key] = None
                            else:
                                cleaned_record[key] = float(value)
                        elif pd.isna(value):
                            cleaned_record[key] = None
                        elif isinstance(value, (np.integer, np.int64, np.int32)):
                            cleaned_record[key] = int(value)
                        elif isinstance(value, (pd.Timestamp, np.datetime64)):
                            cleaned_record[key] = str(value)
                        else:
                            cleaned_record[key] = value
                    
                    # Test if this record is JSON serializable
                    try:
                        json.dumps(cleaned_record, allow_nan=False)
                    except (ValueError, TypeError) as e:
                        logger.error("json_serialization_error", row=idx, error=str(e), record=cleaned_record)
                        # Replace all values with None for this problematic record
                        cleaned_record = {k: None for k in cleaned_record.keys()}
                    
                    data.append(cleaned_record)
                
                logger.info("data_cleaned", total_records=len(data))
                
                return SQLResult(
                    success=True,
                    query=query,
                    query_type=query_type,
                    columns=columns,
                    data=data,
                    row_count=len(data),
                    execution_time_ms=execution_time_ms
                )
            else:
                # Non-SELECT query
                # DuckDB execute returns connection, fetchone needed for some results?
                # .execute() returns a DuckDBPyConnection
                # For non-select, standard sql returns affected rows depending on operation
                # DuckDB python client behaviour check:
                # Often doesn't return rowcount easily for all operations. 
                # Assuming simple success for now.
                
                return SQLResult(
                    success=True,
                    query=query,
                    query_type=query_type,
                    rows_affected=0, # DuckDB specific limitation in some versions
                    execution_time_ms=execution_time_ms
                )
                
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            logger.error("sql_execution_error", query=query[:200], error=error_message)
            
            return SQLResult(
                success=False,
                query=query,
                query_type=query_type,
                execution_time_ms=execution_time_ms,
                error_message=error_message
            )
    
    def explain(self, query: str) -> QueryExplainResult:
        """Get query execution plan."""
        try:
            explain_query = f"EXPLAIN {query}"
            result = self.duckdb.execute(explain_query)
            plan_text = "\n".join(str(row[0]) for row in result.fetchall())
            
            # Try to get analyze info
            try:
                analyze_query = f"EXPLAIN ANALYZE {query}"
                analyze_result = self.duckdb.execute(analyze_query)
                plan_text += "\n\n--- ANALYZE ---\n"
                plan_text += "\n".join(str(row[0]) for row in analyze_result.fetchall())
            except:
                pass
            
            recommendations = self._generate_recommendations(query, plan_text)
            
            return QueryExplainResult(
                query=query,
                plan=QueryPlan(plan_text=plan_text),
                recommendations=recommendations
            )
            
        except Exception as e:
            return QueryExplainResult(
                query=query,
                plan=QueryPlan(plan_text=f"Error: {str(e)}"),
                recommendations=[]
            )
    
    def _generate_recommendations(self, query: str, plan: str) -> List[str]:
        """Generate query optimization recommendations."""
        recommendations = []
        
        query_upper = query.upper()
        
        # Check for SELECT *
        if 'SELECT *' in query_upper:
            recommendations.append("Consider selecting only needed columns instead of SELECT *")
        
        # Check for missing WHERE on UPDATE/DELETE
        if ('UPDATE ' in query_upper or 'DELETE ' in query_upper) and 'WHERE' not in query_upper:
            recommendations.append("WARNING: UPDATE/DELETE without WHERE clause affects all rows")
        
        # Check for DISTINCT on large result sets
        if 'DISTINCT' in query_upper:
            recommendations.append("DISTINCT can be expensive on large datasets. Consider using GROUP BY if applicable")
        
        # Check for multiple table scans in plan
        if plan.lower().count('seq scan') > 1:
            recommendations.append("Multiple sequential scans detected. Consider adding indexes or restructuring joins")
        
        return recommendations
    
    def execute_no_code(self, request: NoCodeQueryRequest) -> SQLResult:
        """Execute a no-code query."""
        query = NoCodeQueryBuilder.build_query(request)
        return self.execute(query, limit=request.limit)
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a table."""
        try:
            result = self.duckdb.execute(f"DESCRIBE {table_name}")
            columns = []
            for row in result.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == 'YES',
                    "key": row[3],
                    "default": row[4]
                })
            return columns
        except Exception as e:
            logger.error("get_schema_error", table=table_name, error=str(e))
            return []
    
    def list_tables(self) -> List[str]:
        """List all available tables in DuckDB."""
        try:
            result = self.duckdb.execute("SHOW TABLES")
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error("list_tables_error", error=str(e))
            return []
