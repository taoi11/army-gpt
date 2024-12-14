import os
import requests
import json
import uuid
import asyncio
from typing import Dict, Optional, Union, AsyncGenerator, List
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.utils.cost import cost_tracker
from .keycheck import credits_checker

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

    async def _primary_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        conversation_history: Optional[List[Message]] = None,
        options: Dict = None,
        request_id: str = None,
        stream: bool = False,
        agent_name: Optional[str] = None
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate completion using primary LLM (OpenRouter)"""
        model = options.get("model")
        if not model:
            raise ValueError("Model not specified in options")
            
        # Use provided messages or format from conversation history
        if not messages:
            messages = self._prepare_messages(prompt, system_prompt, conversation_history, agent_name=agent_name)
        
        prefix = f"[{agent_name}] " if agent_name else ""
        
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
                    "stream": stream,
                    **{k:v for k,v in options.items() if k != "model"}  # Add options except model
                },
                timeout=self.primary_timeout,
                stream=stream
            )
            
            # Log response details only in debug mode
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"{prefix}OpenRouter response status: {response.status_code}")
                if response.status_code != 200:
                    logger.debug(f"{prefix}OpenRouter error response: {response.text}")
            
            response.raise_for_status()

            if stream:
                async def generate():
                    try:
                        for line in response.iter_lines():
                            if line:
                                try:
                                    data = json.loads(line.decode('utf-8').removeprefix('data: '))
                                    if "choices" in data and len(data["choices"]) > 0:
                                        content = data["choices"][0]["delta"].get("content", "")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                        
                        # Track cost after streaming is complete
                        if "id" in data:
                            generation_id = data["id"]
                            logger.debug(f"{prefix}Tracking cost for generation ID: {generation_id}")
                            # Add delay before tracking cost
                            await asyncio.sleep(0.5)  # 500ms delay
                            await cost_tracker.track_api_call(generation_id)
                    except Exception as e:
                        logger.error(f"{prefix}Error in stream processing: {e}")
                        raise
                
                return generate()
            else:
                response_data = response.json()
                result = response_data["choices"][0]["message"]["content"]
                
                # Track cost if generation ID is present
                if "id" in response_data:
                    generation_id = response_data["id"]
                    logger.debug(f"{prefix}Tracking cost for generation ID: {generation_id}")
                    # Add delay before tracking cost
                    await asyncio.sleep(0.5)  # 500ms delay
                    await cost_tracker.track_api_call(generation_id)
                
                # Log truncated response at debug level only
                if logger.isEnabledFor(10):
                    logger.debug(f"{prefix}Response: {truncate_llm_response(result)}")
                    
                return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 402:
                logger.error(f"{prefix}OpenRouter credits exhausted")
                raise ValueError("OpenRouter credits exhausted") from e
            elif response.status_code == 429:
                logger.error(f"{prefix}OpenRouter rate limit exceeded")
                raise ValueError("OpenRouter rate limit exceeded") from e
            elif response.status_code == 500:
                logger.error(f"{prefix}OpenRouter server error: {response.text}")
                raise ValueError("OpenRouter server error") from e
            raise

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        conversation_history: Optional[List[Message]] = None,
        primary_options: Optional[Dict] = None,
        backup_options: Optional[Dict] = None,
        request_id: Optional[str] = None,
        stream: bool = False,
        agent_name: Optional[str] = None
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate completion using primary or backup LLM"""
        try:
            # Format messages
            formatted_messages = self._prepare_messages(
                prompt=prompt,
                system_prompt=system_prompt,
                messages=messages,
                conversation_history=conversation_history,
                agent_name=agent_name
            )
            
            # Try primary LLM first
            try:
                return await self._primary_completion(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=formatted_messages,
                    options=primary_options,
                    request_id=request_id,
                    stream=stream,
                    agent_name=agent_name
                )
            except Exception as e:
                logger.error(f"Primary LLM failed: {str(e)}")
                logger.debug("Falling back to backup LLM")
                
                # Fall back to backup LLM
                return await self._backup_completion(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=formatted_messages,
                    options=backup_options,
                    request_id=request_id,
                    stream=stream,
                    agent_name=agent_name
                )
                
        except Exception as e:
            logger.error(f"LLM completion failed: {str(e)}")
            logger.debug("Full error details:", exc_info=True)
            raise

    def _prepare_messages(
        self, 
        prompt: str, 
        system_prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        conversation_history: Optional[List[Message]] = None,
        agent_name: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages list for API request"""
        formatted_messages = []
        seen_messages = set()  # Initialize seen_messages set
        
        # Add system prompt first if provided
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
            
        # Use provided messages if available, otherwise use conversation history
        if messages:
            # Skip system message if we already added one
            for msg in messages:
                if msg["role"] == "system" and formatted_messages and formatted_messages[0]["role"] == "system":
                    continue
                msg_key = f"{msg['role']}:{msg['content'].strip()}"
                if msg_key not in seen_messages:
                    seen_messages.add(msg_key)
                    formatted_messages.append(msg)
        elif conversation_history:
            # Add conversation history in chronological order
            for msg in conversation_history:
                msg_key = f"{msg.role}:{msg.content.strip()}"
                if msg_key not in seen_messages:
                    seen_messages.add(msg_key)
                    formatted_messages.append(msg.to_dict())
        
        # Add current user prompt if not already in history
        current_prompt_key = f"user:{prompt.strip()}"
        if current_prompt_key not in seen_messages:
            formatted_messages.append({"role": "user", "content": prompt})
        
        # Only log message history in debug mode and if explicitly requested
        if logger.isEnabledFor(10):  # DEBUG level
            truncated_messages = [
                {
                    "role": msg["role"],
                    "content": truncate_llm_response(msg["content"])
                }
                for msg in formatted_messages
            ]
            prefix = f"[{agent_name}] " if agent_name else ""
            logger.debug(f"{prefix}Messages: {json.dumps(truncated_messages, indent=2)}")
        
        return formatted_messages

    async def _backup_completion(
        self, 
        prompt: str, 
        system_prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        conversation_history: Optional[List[Message]] = None,
        options: Dict = None,
        request_id: str = None,
        stream: bool = False,
        agent_name: Optional[str] = None
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate completion using backup LLM (Ollama)"""
        model = options.get("model")
        if not model:
            raise ValueError("Model not specified in options")
            
        # Use provided messages or format from conversation history
        if not messages:
            messages = self._prepare_messages(prompt, system_prompt, conversation_history, agent_name=agent_name)
        
        prefix = f"[{agent_name}] " if agent_name else ""
        
        # Log request details only in debug mode
        if logger.isEnabledFor(10):  # DEBUG level
            logger.debug(f"{prefix}Making backup LLM request to {self.backup_base_url}")
            logger.debug(f"{prefix}Model: {model}")
            logger.debug(f"{prefix}Request ID: {request_id}")
            logger.debug(f"{prefix}Options: {options}")
        
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
            
            response = requests.post(
                f"{self.backup_base_url}/api/chat",
                json=request_data,
                timeout=self.backup_timeout,
                stream=stream  # Enable HTTP streaming
            )
            
            # Log response details only in debug mode
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"{prefix}Backup LLM response status: {response.status_code}")
                logger.debug(f"{prefix}Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            if stream:
                async def generate():
                    try:
                        for line in response.iter_lines():
                            if line:
                                try:
                                    data = json.loads(line.decode('utf-8'))
                                    if "message" in data and "content" in data["message"]:
                                        yield data["message"]["content"]
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        logger.error(f"{prefix}Error in stream processing: {e}")
                        raise
                
                return generate()
            else:
                result = response.json()
                
                # Log response only in debug mode
                if logger.isEnabledFor(10):  # DEBUG level
                    logger.debug(f"{prefix}Response: {truncate_llm_response(result)}")
                
                if "message" in result:
                    return result["message"]["content"]
                
                logger.error(f"{prefix}Unexpected Ollama response format: {result}")
                raise ValueError("Unexpected response format from backup LLM")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"{prefix}Backup LLM request failed: {str(e)}")
            logger.debug(f"{prefix}Full error details:", exc_info=True)
            raise

# Create singleton instance
llm_provider = LLMProvider() 