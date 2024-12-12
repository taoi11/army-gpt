import os
import requests
from typing import Dict, Optional
from src.backend.utils.logger import logger

class LLMProvider:
    def __init__(self):
        self.primary_api_key = os.getenv("OPENROUTER_API_KEY")
        self.primary_base_url = os.getenv("LLM_BASE_URL")
        self.backup_base_url = os.getenv("BACKUP_LLM_BASE_URL")
        self.pace_model = os.getenv("PACE_MODEL")
        self.backup_pace_model = os.getenv("BACKUP_PACE_MODEL")
        
        if not self.primary_api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

    def generate_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 500,
        use_backup: bool = False
    ) -> Optional[str]:
        """Generate completion using either primary or backup LLM"""
        try:
            if not use_backup:
                return self._primary_completion(prompt, system_prompt, temperature, max_tokens)
            return self._backup_completion(prompt, system_prompt, temperature, max_tokens)
        except Exception as e:
            logger.error(f"Error in generate_completion: {str(e)}")
            if not use_backup:
                logger.info("Attempting backup LLM")
                return self.generate_completion(prompt, system_prompt, temperature, max_tokens, use_backup=True)
            return None

    def _primary_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate completion using primary LLM (OpenRouter)"""
        response = requests.post(
            f"{self.primary_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.primary_api_key}",
                "HTTP-Referer": "http://localhost:8020",
                "Content-Type": "application/json"
            },
            json={
                "model": self.pace_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _backup_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate completion using backup LLM (Ollama)"""
        response = requests.post(
            f"{self.backup_base_url}/api/generate",
            json={
                "model": self.backup_pace_model,
                "prompt": f"{system_prompt}\n\nUser: {prompt}\nAssistant:",
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()["response"]

# Create singleton instance
llm_provider = LLMProvider() 