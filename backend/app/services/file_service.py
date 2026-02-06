"""
File Ingestion Service - Enterprise-Grade File Processing
"""
import os
import io
import gzip
import zipfile
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from pathlib import Path
import pandas as pd
import polars as pl
import json

from app.config import settings
from app.models import Dataset, DatasetColumn, DatasetVersion, DatasetStatus, ColumnType
from app.database import get_duckdb, DuckDBManager
from sqlalchemy.orm import Session
import structlog

logger = structlog.get_logger()


class FileIngestionError(Exception):
    """File ingestion error."""
    pass


class SchemaDetector:
    """Detect and map column types from data."""
    
    PANDAS_TO_COLUMN_TYPE = {
        'int64': ColumnType.INTEGER,
        'int32': ColumnType.INTEGER,
        'float64': ColumnType.FLOAT,
        'float32': ColumnType.FLOAT,
        'bool': ColumnType.BOOLEAN,
        'datetime64[ns]': ColumnType.DATETIME,
        'datetime64': ColumnType.DATETIME,
        'object': ColumnType.STRING,
        'string': ColumnType.STRING,
        'category': ColumnType.STRING,
    }
    
    @classmethod
    def detect_column_type(cls, dtype: str) -> ColumnType:
        """Map pandas dtype to ColumnType."""
        dtype_str = str(dtype)
        for key, value in cls.PANDAS_TO_COLUMN_TYPE.items():
            if key in dtype_str.lower():
                return value
        return ColumnType.STRING
    
    @classmethod
    def analyze_dataframe(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze DataFrame and return column metadata."""
        columns = []
        for i, col in enumerate(df.columns):
            col_data = df[col]
            
            # Basic stats
            unique_count = col_data.nunique()
            null_count = col_data.isna().sum()
            
            # Type detection with fallback
            try:
                dtype = cls.detect_column_type(col_data.dtype)
            except:
                dtype = ColumnType.STRING
            
            # Min/max for numeric
            min_val = max_val = avg_val = None
            if dtype in [ColumnType.INTEGER, ColumnType.FLOAT]:
                try:
                    min_val = str(col_data.min())
                    max_val = str(col_data.max())
                    avg_val = str(col_data.mean())
                except:
                    pass
            
            # Sample values - convert to JSON-safe types
            raw_samples = col_data.dropna().head(5).tolist()
            sample_values = []
            for val in raw_samples:
                # Convert numpy/pandas types to native Python types
                if hasattr(val, 'item'):  # numpy scalar
                    sample_values.append(val.item())
                elif hasattr(val, 'isoformat'):  # datetime
                    sample_values.append(val.isoformat())
                elif isinstance(val, (int, float, str, bool, type(None))):
                    sample_values.append(val)
                else:
                    sample_values.append(str(val))
            
            columns.append({
                "name": str(col),
                "original_name": str(col),
                "data_type": dtype.value,
                "position": i,
                "nullable": null_count > 0,
                "unique_count": int(unique_count),
                "null_count": int(null_count),
                "min_value": min_val,
                "max_value": max_val,
                "avg_value": avg_val,
                "sample_values": sample_values
            })
        
        return columns


class FileProcessor:
    """Process various file types."""
    
    SUPPORTED_EXTENSIONS = {
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.csv': 'csv',
        '.tsv': 'tsv',
        '.json': 'json',
        '.txt': 'text',
        '.gz': 'gzip',
        '.zip': 'zip'
    }
    
    def __init__(self, upload_dir: str = None):
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def _get_file_extension(self, filename: str) -> str:
        """Get lowercase file extension."""
        return Path(filename).suffix.lower()
    
    def _generate_virtual_table_name(self, dataset_name: str, dataset_id: int) -> str:
        """Generate unique virtual table name for DuckDB."""
        safe_name = "".join(c if c.isalnum() else "_" for c in dataset_name)
        return f"ds_{dataset_id}_{safe_name[:30]}"
    
    def _save_file(self, file_content: bytes, filename: str) -> str:
        """Save uploaded file to disk."""
        # Generate unique filename
        file_hash = hashlib.md5(file_content[:1024]).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in '.-_' else '_' for c in filename)
        save_path = os.path.join(self.upload_dir, f"{timestamp}_{file_hash}_{safe_name}")
        
        with open(save_path, 'wb') as f:
            f.write(file_content)
        
        return save_path
    
    def read_excel(self, file_path: str, sheet_name: str = None, 
                   skip_rows: int = 0, has_header: bool = True) -> pd.DataFrame:
        """Read Excel file."""
        try:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, 
                                   skiprows=skip_rows, header=0 if has_header else None)
            else:
                # Read first sheet
                df = pd.read_excel(file_path, skiprows=skip_rows, 
                                   header=0 if has_header else None)
            
            # Clean column names
            if not has_header:
                df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
            else:
                df.columns = [str(c).strip() for c in df.columns]
            
            return df
        except Exception as e:
            raise FileIngestionError(f"Failed to read Excel file: {str(e)}")
    
    def get_excel_sheets(self, file_path: str) -> List[str]:
        """Get list of sheet names from Excel file."""
        try:
            xlsx = pd.ExcelFile(file_path)
            return xlsx.sheet_names
        except Exception as e:
            raise FileIngestionError(f"Failed to read Excel sheets: {str(e)}")
    
    def read_csv(self, file_path: str, encoding: str = "utf-8",
                 delimiter: str = ",", skip_rows: int = 0,
                 has_header: bool = True) -> pd.DataFrame:
        """Read CSV/TSV file."""
        try:
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                skiprows=skip_rows,
                header=0 if has_header else None,
                low_memory=False
            )
            
            if not has_header:
                df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
            else:
                df.columns = [str(c).strip() for c in df.columns]
            
            return df
        except Exception as e:
            raise FileIngestionError(f"Failed to read CSV file: {str(e)}")
    
    def read_json(self, file_path: str) -> pd.DataFrame:
        """Read JSON file (array or records)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Check if it's a records format or needs normalization
                if all(isinstance(v, dict) for v in data.values()):
                    df = pd.DataFrame.from_dict(data, orient='index')
                else:
                    df = pd.json_normalize(data)
            else:
                raise FileIngestionError("Unsupported JSON structure")
            
            return df
        except json.JSONDecodeError as e:
            raise FileIngestionError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise FileIngestionError(f"Failed to read JSON file: {str(e)}")
    
    def read_gzip(self, file_path: str, inner_type: str = "csv",
                  **kwargs) -> pd.DataFrame:
        """Read gzipped file."""
        try:
            with gzip.open(file_path, 'rt', encoding=kwargs.get('encoding', 'utf-8')) as f:
                if inner_type == "csv":
                    df = pd.read_csv(f, **kwargs)
                elif inner_type == "json":
                    data = json.load(f)
                    df = pd.DataFrame(data) if isinstance(data, list) else pd.json_normalize(data)
                else:
                    raise FileIngestionError(f"Unsupported inner type: {inner_type}")
            return df
        except Exception as e:
            raise FileIngestionError(f"Failed to read gzip file: {str(e)}")
    
    def process_file(
        self,
        file_content: bytes,
        filename: str,
        config: Dict[str, Any] = None
    ) -> Tuple[pd.DataFrame, str, Dict[str, Any]]:
        """
        Process uploaded file and return DataFrame with metadata.
        
        Returns:
            Tuple of (DataFrame, saved_file_path, file_metadata)
        """
        config = config or {}
        ext = self._get_file_extension(filename)
        
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise FileIngestionError(f"Unsupported file type: {ext}")
        
        # Save file to disk
        file_path = self._save_file(file_content, filename)
        
        file_type = self.SUPPORTED_EXTENSIONS[ext]
        metadata = {
            "file_type": ext.lstrip('.'),
            "file_size": len(file_content),
            "file_path": file_path
        }
        
        try:
            if file_type == 'excel':
                sheet_name = config.get('sheet_name')
                df = self.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    skip_rows=config.get('skip_rows', 0),
                    has_header=config.get('has_header', True)
                )
                # Get sheet names for metadata
                metadata['sheets'] = self.get_excel_sheets(file_path)
                metadata['sheet_name'] = sheet_name or metadata['sheets'][0]
                
            elif file_type == 'csv':
                df = self.read_csv(
                    file_path,
                    encoding=config.get('encoding', 'utf-8'),
                    delimiter=config.get('delimiter', ','),
                    skip_rows=config.get('skip_rows', 0),
                    has_header=config.get('has_header', True)
                )
                
            elif file_type == 'tsv':
                df = self.read_csv(
                    file_path,
                    encoding=config.get('encoding', 'utf-8'),
                    delimiter='\t',
                    skip_rows=config.get('skip_rows', 0),
                    has_header=config.get('has_header', True)
                )
                
            elif file_type == 'json':
                df = self.read_json(file_path)
                
            elif file_type == 'gzip':
                inner_type = config.get('inner_type', 'csv')
                df = self.read_gzip(file_path, inner_type, **config)
                
            elif file_type == 'zip':
                raise FileIngestionError("ZIP file processing requires extraction first")
                
            else:
                # Default to CSV
                df = self.read_csv(file_path, **config)
            
            metadata['row_count'] = len(df)
            metadata['column_count'] = len(df.columns)
            
            return df, file_path, metadata
            
        except FileIngestionError:
            raise
        except Exception as e:
            logger.error("file_processing_error", error=str(e), filename=filename)
            raise FileIngestionError(f"Failed to process file: {str(e)}")


class FileIngestionService:
    """Main service for file ingestion and dataset creation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.processor = FileProcessor()
        self.duckdb = get_duckdb()
    
    def ingest_file(
        self,
        file_content: bytes,
        filename: str,
        dataset_name: str,
        owner_id: int,
        description: str = None,
        config: Dict[str, Any] = None
    ) -> Dataset:
        """
        Ingest a file and create a dataset.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            dataset_name: Name for the dataset
            owner_id: User ID of dataset owner
            description: Optional description
            config: Upload configuration
            
        Returns:
            Created Dataset object
        """
        config = config or {}
        
        # Create dataset record (status: uploading)
        dataset = Dataset(
            name=dataset_name,
            description=description,
            source_type="file",
            source_path=filename,
            owner_id=owner_id,
            status=DatasetStatus.UPLOADING.value
        )
        self.db.add(dataset)
        self.db.flush()  # Get ID
        
        try:
            # Process file
            dataset.status = DatasetStatus.PROCESSING.value
            self.db.commit()
            
            df, file_path, metadata = self.processor.process_file(
                file_content, filename, config
            )
            
            # Update dataset metadata
            dataset.source_path = file_path
            dataset.file_type = metadata['file_type']
            dataset.file_size = metadata['file_size']
            dataset.row_count = metadata['row_count']
            dataset.encoding = config.get('encoding', 'utf-8')
            dataset.delimiter = config.get('delimiter')
            dataset.has_header = config.get('has_header', True)
            dataset.sheet_name = metadata.get('sheet_name')
            
            # Generate virtual table name
            virtual_table_name = self.processor._generate_virtual_table_name(
                dataset_name, dataset.id
            )
            dataset.virtual_table_name = virtual_table_name
            
            # Analyze columns
            column_metadata = SchemaDetector.analyze_dataframe(df)
            
            # Create column records
            for col_meta in column_metadata:
                column = DatasetColumn(
                    dataset_id=dataset.id,
                    **col_meta
                )
                self.db.add(column)
            
            # Register DataFrame in DuckDB
            self.duckdb.register_dataframe(virtual_table_name, df)
            
            # Create initial version
            version = DatasetVersion(
                dataset_id=dataset.id,
                version_number=1,
                snapshot_path=file_path,
                change_type="upload",
                change_summary=f"Initial upload from {filename}",
                changed_by_id=owner_id,
                row_count=metadata['row_count']
            )
            self.db.add(version)
            
            dataset.status = DatasetStatus.READY.value
            self.db.commit()
            
            logger.info(
                "dataset_created",
                dataset_id=dataset.id,
                name=dataset_name,
                rows=metadata['row_count'],
                columns=metadata['column_count']
            )
            
            return dataset
            
        except Exception as e:
            dataset.status = DatasetStatus.ERROR.value
            dataset.error_message = str(e)
            self.db.commit()
            logger.error("ingestion_failed", dataset_id=dataset.id, error=str(e))
            raise
    
    def load_dataset_to_duckdb(self, dataset: Dataset) -> bool:
        """Load an existing dataset into DuckDB memory."""
        if not dataset.source_path or not os.path.exists(dataset.source_path):
            return False
        
        try:
            config = {
                'encoding': dataset.encoding or 'utf-8',
                'delimiter': dataset.delimiter or ',',
                'has_header': dataset.has_header if dataset.has_header is not None else True,
                'sheet_name': dataset.sheet_name
            }
            
            # Resolve file path for Docker environment
            filename = os.path.basename(dataset.source_path)
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            
            # Fallback to source_path if file not found in uploads (dev mode)
            if not os.path.exists(file_path) and os.path.exists(dataset.source_path):
                file_path = dataset.source_path
                
            if not os.path.exists(file_path):
                 logger.error("file_not_found", path=file_path)
                 return False

            df, _, _ = self.processor.process_file(
                open(file_path, 'rb').read(),
                filename,
                config
            )
            
            self.duckdb.register_dataframe(dataset.virtual_table_name, df)
            return True
            
        except Exception as e:
            logger.error("load_dataset_failed", dataset_id=dataset.id, error=str(e))
            return False
    
    def get_dataset_dataframe(self, dataset: Dataset) -> pd.DataFrame:
        """Get DataFrame for a dataset from DuckDB."""
        try:
            return self.duckdb.query_df(f"SELECT * FROM {dataset.virtual_table_name}")
        except:
            # Try to reload
            if self.load_dataset_to_duckdb(dataset):
                return self.duckdb.query_df(f"SELECT * FROM {dataset.virtual_table_name}")
            raise FileIngestionError(f"Dataset {dataset.name} not available")

    def get_dataset_preview(self, dataset: Dataset, limit: int = 10) -> pd.DataFrame:
        """Get preview DataFrame for a dataset from DuckDB."""
        # Verify table exists in memory first
        try:
            check_query = f"SELECT count(*) as cnt FROM information_schema.tables WHERE table_name = '{dataset.virtual_table_name}'"
            res = self.duckdb.execute(check_query).fetchone()
            
            if not res or res[0] == 0:
                # Try one last attempt to reload ONLY if file exists in correct location
                # This respects the "remove dependency" request by not failing on path errors if table exists
                # but still trying to recover if possible without crashing
                if self.load_dataset_to_duckdb(dataset):
                    return self.duckdb.query_df(f"SELECT * FROM {dataset.virtual_table_name} LIMIT {limit}")
                
                raise FileIngestionError(f"Dataset table '{dataset.virtual_table_name}' not found in memory. Please reload the dataset in Data Sources.")

            return self.duckdb.query_df(f"SELECT * FROM {dataset.virtual_table_name} LIMIT {limit}")
        except Exception as e:
            if "not found" in str(e).lower():
                 raise FileIngestionError(f"Dataset not loaded: {str(e)}")
            raise e
