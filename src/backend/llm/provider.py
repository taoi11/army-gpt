import os
import requests
import json
import uuid
from typing import Dict, Optional, Union, Generator, List
from src.backend.utils.logger import logger
from .keycheck import CREDITS_AVAILABLE

class Message:
    """Represents a message in the conversation"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {
            "role": self.role,
            "content": self.content
        }

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
        conversation_history: Optional[List[Message]] = None,
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
                return self._backup_completion(
                    prompt, 
                    system_prompt, 
                    conversation_history,
                    backup_options or {}, 
                    request_id, 
                    stream
                )
            
            # Try primary LLM
            return self._primary_completion(
                prompt, 
                system_prompt, 
                conversation_history,
                primary_options or {}, 
                request_id
            )
        except Exception as e:
            # If primary fails, try backup
            logger.error(f"Primary LLM error: {str(e)}")
            try:
                return self._backup_completion(
                    prompt, 
                    system_prompt, 
                    conversation_history,
                    backup_options or {}, 
                    request_id, 
                    stream
                )
            except Exception as backup_error:
                logger.error(f"Backup LLM error: {str(backup_error)}")
                raise  # Re-raise the backup error

    def _prepare_messages(
        self, 
        prompt: str, 
        system_prompt: str,
        conversation_history: Optional[List[Message]] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages list for API request"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend([msg.to_dict() for msg in conversation_history])
        
        # Add current user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Log full conversation history
        logger.debug(f"Prepared messages ({len(messages)} total):")
        for msg in messages:
            logger.debug(f"- {msg['role']}: {truncate_llm_response(msg['content'])}")
        
        return messages

    def _primary_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        conversation_history: Optional[List[Message]],
        options: Dict,
        request_id: str
    ) -> str:
        """Generate completion using primary LLM (OpenRouter)"""
        model = options.get("model")
        if not model:
            raise ValueError("Model not specified in options")
            
        messages = self._prepare_messages(prompt, system_prompt, conversation_history)
        
        try:
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
                    "messages": messages,
                    **{k:v for k,v in options.items() if k != "model"}  # Add options except model
                },
                timeout=self.primary_timeout
            )
            
            # Log response details in debug mode
            logger.debug(f"OpenRouter response status: {response.status_code}")
            if response.status_code != 200:
                logger.debug(f"OpenRouter error response: {response.text}")
            
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 402:
                logger.error("OpenRouter credits exhausted")
                raise ValueError("OpenRouter credits exhausted") from e
            elif response.status_code == 429:
                logger.error("OpenRouter rate limit exceeded")
                raise ValueError("OpenRouter rate limit exceeded") from e
            elif response.status_code == 500:
                logger.error(f"OpenRouter server error: {response.text}")
                raise ValueError("OpenRouter server error") from e
            raise

    def _backup_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        conversation_history: Optional[List[Message]],
        options: Dict,
        request_id: str,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """Generate completion using backup LLM (Ollama)"""
        model = options.get("model")
        if not model:
            raise ValueError("Model not specified in options")
            
        messages = self._prepare_messages(prompt, system_prompt, conversation_history)
        
        # Log request details
        logger.debug(f"Making backup LLM request to {self.backup_base_url}")
        logger.debug(f"Model: {model}")
        logger.debug(f"Request ID: {request_id}")
        logger.debug(f"Options: {options}")
        
        # Log messages with truncated content
        truncated_messages = [
            {
                "role": msg["role"],
                "content": msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            }
            for msg in messages
        ]
        logger.debug(f"Messages: {json.dumps(truncated_messages, indent=2)}")
        
        try:
            # Format request according to Ollama API
            request_data = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": options.get("temperature", 0.1),
                    "num_ctx": options.get("num_ctx", 2048),
                    "num_predict": options.get("num_batch", 128)
                }
            }
            
            # Log formatted request with truncated messages
            truncated_request = {
                **request_data,
                "messages": truncated_messages
            }
            logger.debug(f"Formatted Ollama request: {json.dumps(truncated_request, indent=2)}")
            
            response = requests.post(
                f"{self.backup_base_url}/api/chat",
                json=request_data,
                timeout=self.backup_timeout,
                stream=stream  # Enable HTTP streaming
            )
            
            # Log response details
            logger.debug(f"Backup LLM response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            if stream:
                def generate():
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                logger.debug(f"Stream chunk: {chunk}")
                                if "message" in chunk and chunk["message"].get("content"):
                                    yield chunk["message"]["content"]
                            except json.JSONDecodeError as e:
                                logger.error(f"Error decoding streaming response: {e}")
                                continue
                return generate()
            
            result = response.json()
            logger.debug(f"Backup LLM response content: {result}")
            
            if "message" in result:
                return result["message"]["content"]
            
            logger.error(f"Unexpected Ollama response format: {result}")
            raise ValueError("Unexpected response format from backup LLM")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Backup LLM request failed: {str(e)}")
            logger.debug("Full error details:", exc_info=True)
            raise

# Create singleton instance
llm_provider = LLMProvider() 