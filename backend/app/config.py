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
    
    # Application Internal Database (ONLY from env)
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/AI_Data_Management"
    
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
