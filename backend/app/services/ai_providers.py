"""
AI Provider Abstraction Layer
Supports multiple AI providers: Ollama (local), Google Gemini, OpenAI, HuggingFace
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import httpx
import structlog

logger = structlog.get_logger()


class AIProviderError(Exception):
    """Base exception for AI provider errors."""
    pass


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models from this provider."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the provider is accessible and credentials are valid."""
        pass


from app.config import settings

class OllamaProvider(BaseAIProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('url') or config.get('api_url') or settings.OLLAMA_URL
        self.default_model = config.get('model', 'llama2')
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return [m["name"] for m in models]
                return []
        except Exception as e:
            logger.error("ollama_list_models_error", error=str(e))
            return []
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text using Ollama."""
        target_model = model or self.default_model
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": target_model,
                        "prompt": prompt,
                        "system": system,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    }
                )
                response.raise_for_status()
                return response.json()["response"]
        except Exception as e:
            logger.error("ollama_generate_error", error=str(e), model=target_model)
            raise AIProviderError(f"Ollama generation failed: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test Ollama connection."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


class GoogleProvider(BaseAIProvider):
    """Google Gemini AI provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.default_model = config.get('model', 'gemini-pro')
        
        if not self.api_key:
            raise AIProviderError("Google API key is required")
        
        # Import here to avoid dependency if not used
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
        except ImportError:
            raise AIProviderError("google-generativeai package not installed")
    
    async def get_available_models(self) -> List[str]:
        """Get available Gemini models."""
        try:
            models = self.genai.list_models()
            return [m.name.split('/')[-1] for m in models if 'generateContent' in m.supported_generation_methods]
        except Exception as e:
            logger.error("google_list_models_error", error=str(e))
            return ['gemini-pro', 'gemini-pro-vision']  # Fallback to known models
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text using Google Gemini."""
        target_model = model or self.default_model
        
        try:
            model_instance = self.genai.GenerativeModel(target_model)
            
            # Combine system and prompt if system is provided
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            
            response = model_instance.generate_content(
                full_prompt,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_tokens,
                }
            )
            return response.text
        except Exception as e:
            logger.error("google_generate_error", error=str(e), model=target_model)
            raise AIProviderError(f"Google Gemini generation failed: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test Google API connection."""
        try:
            models = self.genai.list_models()
            return len(list(models)) > 0
        except Exception:
            return False


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.default_model = config.get('model', 'gpt-3.5-turbo')
        
        if not self.api_key:
            raise AIProviderError("OpenAI API key is required")
        
        # Import here to avoid dependency if not used
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise AIProviderError("openai package not installed")
    
    async def get_available_models(self) -> List[str]:
        """Get available OpenAI models."""
        try:
            models = await self.client.models.list()
            # Filter to only chat models
            chat_models = [m.id for m in models.data if 'gpt' in m.id.lower()]
            return sorted(chat_models)
        except Exception as e:
            logger.error("openai_list_models_error", error=str(e))
            return ['gpt-4', 'gpt-4-turbo-preview', 'gpt-3.5-turbo']  # Fallback
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text using OpenAI."""
        target_model = model or self.default_model
        
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("openai_generate_error", error=str(e), model=target_model)
            raise AIProviderError(f"OpenAI generation failed: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test OpenAI API connection."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False


class HuggingFaceProvider(BaseAIProvider):
    """HuggingFace Inference API provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.default_model = config.get('model', 'mistralai/Mistral-7B-Instruct-v0.2')
        
        if not self.api_key:
            raise AIProviderError("HuggingFace API key is required")
        
        # Use official HuggingFace Async client
        try:
            from huggingface_hub import AsyncInferenceClient
            self.client = AsyncInferenceClient(token=self.api_key)
        except ImportError:
            raise AIProviderError("huggingface_hub package not installed")
    
    async def get_available_models(self) -> List[str]:
        """
        Get verified working HuggingFace models.
        Ports logic from Data Analysis ChatBoat reference.
        """
        try:
            import httpx
            import asyncio
            
            # Step 1: Query Hub for popular text-generation models
            # We use httpx instead of requests for async support
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.get(
                    "https://huggingface.co/api/models",
                    params={
                        "pipeline_tag": "text-generation",
                        "sort": "downloads",
                        "direction": "-1",
                        "limit": 50,  # Get more candidates
                        "filter": "text-generation"
                    }
                )
                
                if response.status_code != 200:
                    return self._get_fallback_models()
                
                models_data = response.json()
            
            # Filter candidates
            candidates = [
                m["modelId"] for m in models_data 
                if not m.get("gated", False) and not m.get("private", False)
            ]
            
            # Prioritize models known to be good for chat/instruction following
            priority_keywords = [
                "instruct", "chat", "conversational", "assistant",
                "flan", "zephyr", "mistral", "llama", "phi", "gemma", "qwen"
            ]
            
            # Sort candidates
            prioritized = []
            others = []
            
            for model in candidates:
                model_lower = model.lower()
                if any(kw in model_lower for kw in priority_keywords):
                    prioritized.append(model)
                else:
                    others.append(model)
            
            # Combine and limit
            test_order = prioritized + others
            test_limit = 15  # Limit verification to top 15 candidates
            test_order = test_order[:test_limit]
            
            # Step 2: Verify connectivity for each model (in parallel)
            working_models = []
            
            # Define verifier function (runs in thread pool)
            loop = asyncio.get_event_loop()
            tasks = []
            
            for model_id in test_order:
                tasks.append(loop.run_in_executor(
                    None, 
                    lambda m=model_id: self._verify_model(m)
                ))
            
            # Wait for all verifications
            results = await asyncio.gather(*tasks)
            
            for model_id, works in zip(test_order, results):
                if works:
                    working_models.append(model_id)
            
            if working_models:
                return working_models
            
            return self._get_fallback_models()
            
        except Exception as e:
            logger.error("huggingface_discovery_error", error=str(e))
            return self._get_fallback_models()
    
    def _get_fallback_models(self) -> List[str]:
        """Return reliable fallback models."""
        return [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "microsoft/Phi-3-mini-4k-instruct",
            "google/gemma-1.1-7b-it",
            "HuggingFaceH4/zephyr-7b-beta"
        ]
        
    def _verify_model(self, model_id: str) -> bool:
        """Synchronously verify if a model works (for executor)."""
        try:
            # Try chat completion first
            try:
                self.client.chat_completion(
                    model=model_id,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5
                )
                return True
            except:
                pass
            
            # Try text generation fallback
            try:
                self.client.text_generation(
                    "Hi",
                    model=model_id,
                    max_new_tokens=5
                )
                return True
            except:
                return False
        except:
            return False

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text using HuggingFace Inference API."""
        target_model = model or self.default_model
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Define generation task
            def _generate():
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                
                try:
                    # Try chat completion first
                    response = self.client.chat_completion(
                        model=target_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    if response and response.choices:
                        return response.choices[0].message.content
                except Exception:
                    # Fallback to text generation
                    full_prompt = f"{system}\n\n{prompt}" if system else prompt
                    return self.client.text_generation(
                        full_prompt,
                        model=target_model,
                        max_new_tokens=max_tokens,
                        temperature=temperature,
                        return_full_text=False
                    )
            
            # Run in executor
            return await loop.run_in_executor(None, _generate)
            
        except Exception as e:
            logger.error("huggingface_generate_error", error=str(e), model=target_model)
            raise AIProviderError(f"HuggingFace generation failed: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test HuggingFace API connection."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Use gpt2 for quick connectivity check
            return await loop.run_in_executor(
                None,
                lambda: self._verify_model("gpt2")
            )
        except Exception as e:
            logger.error("huggingface_test_error", error=str(e))
            return False


# Provider factory
def create_provider(provider_type: str, config: Dict[str, Any]) -> BaseAIProvider:
    """Factory function to create AI providers."""
    providers = {
        'ollama': OllamaProvider,
        'google': GoogleProvider,
        'openai': OpenAIProvider,
        'huggingface': HuggingFaceProvider
    }
    
    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise AIProviderError(f"Unknown provider type: {provider_type}")
    
    return provider_class(config)
