"""
AI Configuration Model
Stores AI provider settings and API keys
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class AIConfig(Base):
    """AI provider configuration."""
    __tablename__ = "ai_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)  # 'ollama', 'google', 'openai', 'huggingface'
    model_name = Column(String(255), nullable=True)
    api_key = Column(Text, nullable=True)  # Encrypted in production
    api_url = Column(String(500), nullable=True)  # For Ollama or custom endpoints
    is_active = Column(Boolean, default=False)  # Only one config can be active
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AIConfig(provider='{self.provider}', model='{self.model_name}', active={self.is_active})>"
