import os
import requests
import json
from typing import Dict, Optional
from src.backend.utils.logger import logger
from .keycheck import CREDITS_AVAILABLE

class LLMProvider:
    def __init__(self):
        self.primary_api_key = os.getenv("OPENROUTER_API_KEY")
        self.primary_base_url = os.getenv("LLM_BASE_URL")
        self.backup_base_url = os.getenv("BACKUP_LLM_BASE_URL")
        self.pace_model = os.getenv("PACE_MODEL")
        self.backup_pace_model = os.getenv("BACKUP_PACE_MODEL")
        
        # Timeouts in seconds (connect_timeout, read_timeout)
        self.primary_timeout = (5.0, 30.0)   # 5s connect, 30s read
        self.backup_timeout = (5.0, 90.0)    # 5s connect, 90s read
        
        if not self.primary_api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

    def generate_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        temperature: float = 0.1,
    ) -> Optional[str]:
        """Generate completion using either primary or backup LLM based on credits"""
        try:
            # Use backup if no credits available
            if not CREDITS_AVAILABLE:
                logger.info("No credits available, using backup LLM")
                return self._backup_completion(prompt, system_prompt, temperature)
            
            # Try primary LLM
            return self._primary_completion(prompt, system_prompt, temperature)
        except Exception as e:
            # If primary fails, try backup
            logger.error(f"Primary LLM error: {str(e)}")
            return self._backup_completion(prompt, system_prompt, temperature)

    def _primary_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        temperature: float
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
                "temperature": temperature
            },
            timeout=self.primary_timeout
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _backup_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        temperature: float
    ) -> str:
        """Generate completion using backup LLM (Ollama)"""
        response = requests.post(
            f"{self.backup_base_url}/api/generate",
            json={
                "model": self.backup_pace_model,
                "prompt": f"{system_prompt}\n\nUser: {prompt}\nAssistant:",
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            },
            timeout=self.backup_timeout
        )
        response.raise_for_status()
        
        result = response.json()
        if "response" in result:
            return result["response"]
        
        logger.error(f"Unexpected Ollama response format: {result}")
        raise ValueError("Unexpected response format from backup LLM")

# Create singleton instance
llm_provider = LLMProvider() 