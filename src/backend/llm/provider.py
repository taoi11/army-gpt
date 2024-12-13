import os
import requests
import json
import uuid
from typing import Dict, Optional, Union, Generator
from src.backend.utils.logger import logger
from .keycheck import CREDITS_AVAILABLE

class LLMProvider:
    def __init__(self):
        # Load environment variables
        self.primary_api_key = os.getenv("OPENROUTER_API_KEY")
        self.primary_base_url = os.getenv("LLM_BASE_URL")
        self.backup_base_url = os.getenv("BACKUP_LLM_BASE_URL")
        
        # Timeouts in seconds (connect_timeout, read_timeout)
        self.primary_timeout = (5.0, 30.0)   # 5s connect, 30s read
        self.backup_timeout = (5.0, 90.0)    # 5s connect, 90s read
        
        if not self.primary_api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

    def generate_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        primary_options: Dict = None,
        backup_options: Dict = None,
        request_id: str = None,
        stream: bool = False
    ) -> Optional[str]:
        """Generate completion using either primary or backup LLM based on credits"""
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())

        try:
            # Use backup if no credits available
            if not CREDITS_AVAILABLE:
                logger.info("No credits available, using backup LLM")
                return self._backup_completion(prompt, system_prompt, backup_options or {}, request_id, stream)
            
            # Try primary LLM
            return self._primary_completion(prompt, system_prompt, primary_options or {}, request_id)
        except Exception as e:
            # If primary fails, try backup
            logger.error(f"Primary LLM error: {str(e)}")
            try:
                return self._backup_completion(prompt, system_prompt, backup_options or {}, request_id, stream)
            except Exception as backup_error:
                logger.error(f"Backup LLM error: {str(backup_error)}")
                raise  # Re-raise the backup error

    def _primary_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        options: Dict,
        request_id: str
    ) -> str:
        """Generate completion using primary LLM (OpenRouter)"""
        model = options.pop("model", None)
        if not model:
            raise ValueError("Model not specified in options")
            
        response = requests.post(
            f"{self.primary_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.primary_api_key}",
                "HTTP-Referer": "https://github.com/taoi11/army-gpt",
                "X-Title": "Army-GPT",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                **options  # Add any additional options
            },
            timeout=self.primary_timeout
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _backup_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        options: Dict,
        request_id: str,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """Generate completion using backup LLM (Ollama)"""
        model = options.pop("model", None)
        if not model:
            raise ValueError("Model not specified in options")
            
        response = requests.post(
            f"{self.backup_base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": stream,
                "options": options
            },
            timeout=self.backup_timeout,
            stream=stream  # Enable HTTP streaming
        )
        response.raise_for_status()
        
        if stream:
            def generate():
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and chunk["message"].get("content"):
                                yield chunk["message"]["content"]
                        except json.JSONDecodeError as e:
                            logger.error(f"Error decoding streaming response: {e}")
                            continue
            return generate()
        
        result = response.json()
        if "message" in result:
            return result["message"]["content"]
        
        logger.error(f"Unexpected Ollama response format: {result}")
        raise ValueError("Unexpected response format from backup LLM")

# Create singleton instance
llm_provider = LLMProvider() 