"""
AI Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.database import get_db
from app.database import get_db
from app.models.ai_config import AIConfig
from app.core.rbac import get_current_active_user
from app.services.ai_providers import create_provider, AIProviderError
from app.services.ai_service import AIService
from app.config import settings

router = APIRouter(tags=["ai"])

# Pydantic models
class AIProviderInfo(BaseModel):
    id: str
    name: str
    is_cloud: bool
    requires_api_key: bool

class AIConfigCreate(BaseModel):
    provider: str
    model_name: str
    api_key: str | None = None
    api_url: str | None = None
    make_active: bool = True

class AIConfigResponse(BaseModel):
    id: int
    provider: str
    model_name: str | None
    is_active: bool
    created_at: Any

class ModelListResponse(BaseModel):
    provider: str
    models: List[str]

# Available providers
PROVIDERS = [
    {"id": "ollama", "name": "Ollama (Local)", "is_cloud": False, "requires_api_key": False},
    {"id": "google", "name": "Google Gemini", "is_cloud": True, "requires_api_key": True},
    {"id": "openai", "name": "OpenAI GPT", "is_cloud": True, "requires_api_key": True},
    {"id": "huggingface", "name": "HuggingFace", "is_cloud": True, "requires_api_key": True},
]

@router.get("/providers", response_model=List[AIProviderInfo])
async def get_providers(current_user = Depends(get_current_active_user)):
    """List available AI providers."""
    return PROVIDERS

@router.get("/config", response_model=List[AIConfigResponse])
async def get_configs(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get all AI configurations."""
    configs = db.query(AIConfig).order_by(AIConfig.id.desc()).all()
    return configs

@router.get("/config/active", response_model=AIConfigResponse | None)
async def get_active_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get currently active AI configuration."""
    config = db.query(AIConfig).filter(AIConfig.is_active == True).first()
    if not config:
        # Fallback to default Ollama if not configured?
        # Or return null to prompt user to configure.
        return None
    return config

@router.post("/config", response_model=AIConfigResponse)
async def create_config(
    config_in: AIConfigCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create or update AI configuration."""
    # If active, deactivate others
    if config_in.make_active:
        db.query(AIConfig).update({"is_active": False})
    
    # Check if config exists for this provider/model combo to reuse?
    # For now, just create new entry or update existing singleton per provider?
    # Let's keep it simple: Create new entry.
    
    db_config = AIConfig(
        provider=config_in.provider,
        model_name=config_in.model_name,
        api_key=config_in.api_key,
        api_url=config_in.api_url,
        is_active=config_in.make_active
    )
    
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.post("/test")
async def test_connection(
    config_in: AIConfigCreate,
    current_user = Depends(get_current_active_user)
):
    """Test connection with provided credentials."""
    try:
        provider_config = {
            "api_key": config_in.api_key,
            "url": config_in.api_url,
            "model": config_in.model_name
        }
        
        provider = create_provider(config_in.provider, provider_config)
        success = await provider.test_connection()
        
        if success:
            return {"success": True, "message": "Connection successful"}
        else:
            return {"success": False, "message": "Connection failed. Please check your credentials."}
            
    except AIProviderError as e:
        # Provider-specific errors (e.g., missing API key)
        return {"success": False, "message": str(e)}
    except Exception as e:
        # Generic errors
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"Error: {str(e)}"}

@router.get("/models", response_model=ModelListResponse)
async def list_models(
    provider: str,
    api_key: str | None = None,
    api_url: str | None = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Fetch available models for a provider on-the-fly."""
    try:
        # If no API key provided, try to find active config for this provider
        if not api_key:
            # Check for active config
            config = db.query(AIConfig).filter(
                AIConfig.provider == provider,
                AIConfig.is_active == True
            ).first()
            
            if config and config.api_key:
                api_key = config.api_key
            
            # If still no key and not active, maybe verify if we have a non-active one?
            # For now, stick to active config to avoid confusion.
            # If nothing found and provider requires key, creates_provider will fail.

        provider_config = {"api_key": api_key, "url": api_url}
        prov_instance = create_provider(provider, provider_config)
        models = await prov_instance.get_available_models()
        return {"provider": provider, "models": models}
    except Exception as e:
        # Log the error for debugging
        print(f"Error listing models for {provider}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
