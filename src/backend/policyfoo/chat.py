import os
import re
from typing import Optional, Dict, Union, Generator, List, AsyncGenerator
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.llm.provider import llm_provider, Message
import uuid
import json

class ChatAgent:
    """Agent for generating chat responses based on policy content"""
    
    def __init__(self):
        self.PRIMARY_OPTIONS = {
            "model": os.getenv("CHAT_AGENT_MODEL"),
            "temperature": 0.1
        }
        
        self.BACKUP_OPTIONS = {
            "model": os.getenv("BACKUP_CHAT_AGENT_MODEL"),
            "temperature": 0.1,
            "num_ctx": int(os.getenv("BACKUP_CHAT_AGENT_NUM_CTX")),
            "num_batch": int(os.getenv("BACKUP_CHAT_AGENT_BATCH_SIZE"))
        }
        
    def load_system_prompt(self) -> Optional[str]:
        """Load the system prompt for chat responses"""
        try:
            prompt_path = os.path.join("src", "prompts", "chatAgent.md")
            if not os.path.exists(prompt_path):
                logger.error(f"System prompt not found at {prompt_path}")
                return None
                
            with open(prompt_path, 'r') as f:
                return f.read().strip()
                
        except Exception as e:
            logger.error(f"Error loading system prompt: {str(e)}")
            return None

    async def _format_messages(
        self,
        query: str,
        policy_content: str,
        conversation_history: Optional[List[Message]] = None
    ) -> List[Dict[str, str]]:
        """Format conversation history into messages for the LLM API"""
        formatted_messages = []
        seen_messages = set()  # Initialize seen_messages set
        
        # Load and prepare system prompt first
        system_prompt = self.load_system_prompt()
        if system_prompt:
            # Handle policy content if it's an async generator
            content_str = policy_content
            if hasattr(policy_content, '__aiter__'):
                try:
                    content_str = ""
                    async for chunk in policy_content:
                        content_str += chunk
                except Exception as e:
                    logger.error(f"Error reading policy content stream: {e}")
                    content_str = "Error reading policy content"

            # Replace policy content placeholder with raw content
            system_prompt = system_prompt.replace("{{POLICY_DATA}}", content_str)
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history in chronological order
        if conversation_history:
            # Convert Message objects to dicts and filter out duplicates
            for msg in conversation_history:
                # Create a unique key for the message
                msg_key = f"{msg.role}:{msg.content.strip()}"
                if msg_key not in seen_messages:
                    seen_messages.add(msg_key)
                    formatted_messages.append(msg.to_dict())
        
        # Add current user prompt if not already in history
        current_prompt_key = f"user:{query.strip()}"
        if current_prompt_key not in seen_messages:
            formatted_messages.append({"role": "user", "content": query})
        
        return formatted_messages

    async def generate_response(
        self,
        query: str,
        policy_content: str,
        request_id: str,
        conversation_history: Optional[List[Message]] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a response to the user's query"""
        try:
            # Format messages with conversation history
            messages = await self._format_messages(query, policy_content, conversation_history)
            
            # Create copies of options to avoid modifying class-level dictionaries
            primary_options = self.PRIMARY_OPTIONS.copy()
            backup_options = self.BACKUP_OPTIONS.copy()
            
            # Override temperature if provided
            if temperature is not None:
                primary_options["temperature"] = temperature
                backup_options["temperature"] = temperature
            
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"[ChatAgent] Making LLM request for chat response")
                logger.debug(f"[ChatAgent] Query: {truncate_llm_response(query)}")
                logger.debug(f"[ChatAgent] Request ID: {request_id}")
                
            # Generate response
            response = await llm_provider.generate_completion(
                prompt=query,  # Pass original query
                system_prompt=messages[0]["content"] if messages else "",  # Use the system prompt from messages
                messages=messages,  # Pass formatted messages directly
                primary_options=primary_options,
                backup_options=backup_options,
                request_id=request_id,
                agent_name="ChatAgent"  # Add agent name to identify messages
            )
            
            # Return response directly - let frontend handle parsing
            return response
            
        except Exception as e:
            logger.error(f"[ChatAgent] Error generating chat response: {str(e)}")
            # Return error message for frontend to parse
            async def error_generator():
                yield "<response><answer>I apologize, but I encountered an error while processing your request. Please try again.</answer><citations></citations><follow_up>Try rephrasing your question?</follow_up></response>"
            return error_generator()

# Create singleton instance
chat_agent = ChatAgent() 