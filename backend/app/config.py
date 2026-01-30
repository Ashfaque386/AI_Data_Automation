"""
Enterprise Data Operations Platform - Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "Enterprise Data Operations Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/dataops"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_EXTENSIONS: list = [".xlsx", ".xls", ".csv", ".tsv", ".json", ".txt", ".zip", ".gz"]
    
    # DuckDB
    DUCKDB_PATH: str = "./data/analytics.duckdb"
    
    # AI/LLM
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    AI_ENABLED: bool = True
    
    # Redis (for task queue)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_db_url(self) -> str:
        """Get database URL, checking persistent config first."""
        # Use absolute path relative to app root to avoid CWD issues
        # config.py is in app/config.py, so app root is ../
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(app_root, "data", "db_config.json")
        
        print(f"DEBUG: Checking config at {config_path}")
        parent = os.path.dirname(config_path)
        if os.path.exists(parent):
            print(f"DEBUG: Parent {parent} exists. Contents: {os.listdir(parent)}")
        else:
             print(f"DEBUG: Parent {parent} does not exist!")

        if os.path.exists(config_path):
            import json
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    print(f"DEBUG: JSON keys: {list(data.keys())}")
                    if "database_url" in data:
                        print(f"DEBUG: Found config: {data['database_url']}")
                        return data["database_url"]
            except Exception as e:
                print(f"Error loading db_config: {e}")
                pass
        
        print("DEBUG: Using default DATABASE_URL")
        return self.DATABASE_URL
    
    def save_db_config(self, database_url: str):
        """Save database configuration."""
        config_path = "./data/db_config.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        import json
        with open(config_path, "w") as f:
            json.dump({"database_url": database_url}, f)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
