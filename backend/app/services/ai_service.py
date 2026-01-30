"""
AI Service - Integration with Ollama/LLM
"""
from typing import Optional, Dict, Any
import httpx
import json
import structlog

from app.config import settings

logger = structlog.get_logger()


class AIServiceError(Exception):
    """AI service error."""
    pass


class OllamaClient:
    """Client for Ollama local LLM."""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL
        self.enabled = settings.AI_ENABLED
    
    async def get_available_models(self) -> list:
        """Get list of available Ollama models."""
        if not self.enabled:
            return []
        
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
        """Generate text from prompt."""
        if not self.enabled:
            raise AIServiceError("AI features are disabled")
        
        # Use provided model or fall back to default
        target_model = model or self.model
        
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
            logger.error("ollama_error", error=str(e), model=target_model)
            raise AIServiceError(f"Ollama request failed: {str(e)}")


class AIService:
    """AI service for data operations."""
    
    def __init__(self):
        self.ollama = OllamaClient()
    
    async def get_available_models(self) -> list:
        """Get available models."""
        return await self.ollama.get_available_models()
    
    async def natural_language_to_sql(
        self,
        natural_query: str,
        tables_schema: Dict[str, Any],
        model: Optional[str] = None
    ) -> str:
        """Convert natural language to SQL query."""
        system_prompt = """You are a SQL expert. Convert natural language queries to SQL.
Only respond with the SQL query, no explanations.

Available tables and their schemas:
"""
        
        for table, schema in tables_schema.items():
            system_prompt += f"\n{table}:\n"
            for col in schema:
                system_prompt += f"  - {col['name']} ({col['type']})\n"
        
        prompt = f"Convert this to SQL: {natural_query}"
        
        try:
            sql = await self.ollama.generate(
                prompt=prompt,
                system=system_prompt,
                model=model,
                temperature=0.3
            )
            return sql.strip()
        except Exception as e:
            logger.error("nl_to_sql_error", error=str(e))
            raise AIServiceError(f"NL to SQL failed: {str(e)}")
    
    async def suggest_formula(
        self,
        description: str,
        column_names: list,
        model: Optional[str] = None
    ) -> str:
        """Suggest Excel formula based on description."""
        system_prompt = f"""You are an Excel formula expert. Create Excel-compatible formulas.
Only respond with the formula, starting with =.

Available columns: {', '.join(column_names)}
"""
        
        prompt = f"Create a formula for: {description}"
        
        try:
            formula = await self.ollama.generate(
                prompt=prompt,
                system=system_prompt,
                model=model,
                temperature=0.3
            )
            
            if not formula.startswith('='):
                formula = '=' + formula
            
            return formula.strip()
        except Exception as e:
            logger.error("formula_suggest_error", error=str(e))
            raise AIServiceError(f"Formula suggestion failed: {str(e)}")
    
    async def detect_data_quality_issues(
        self,
        dataset_summary: Dict[str, Any],
        model: Optional[str] = None
    ) -> list:
        """Detect potential data quality issues."""
        system_prompt = """You are a data quality expert. Analyze dataset summaries and identify potential issues.
Respond with a JSON array of issues, each with: {"type": "...", "column": "...", "description": "...", "severity": "low|medium|high"}
"""
        
        prompt = f"Analyze this dataset summary:\n{json.dumps(dataset_summary, indent=2)}"
        
        try:
            response = await self.ollama.generate(
                prompt=prompt,
                system=system_prompt,
                model=model,
                temperature=0.5
            )
            
            # Simple cleanup if the model returns markdown code blocks
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response.replace("```json", "").replace("```", "")
            elif clean_response.startswith("```"):
                clean_response = clean_response.replace("```", "")
            
            issues = json.loads(clean_response)
            return issues
        except Exception as e:
            logger.error("quality_detection_error", error=str(e))
            return []
    
    async def classify_column(self, column_name: str, sample_values: list, model: Optional[str] = None) -> str:
        """Classify column type/category."""
        system_prompt = """You are a data categorization expert. Classify columns based on name and sample values.
Respond with ONE of: email, phone, address, name, date, currency, percentage, text, number, category, id, other
"""
        
        prompt = f"Column: {column_name}\nSample values: {sample_values[:10]}"
        
        try:
            classification = await self.ollama.generate(
                prompt=prompt,
                system=system_prompt,
                model=model,
                temperature=0.2,
                max_tokens=20
            )
            return classification.strip().lower()
        except Exception as e:
            logger.error("column_classify_error", error=str(e))
            return "other"
