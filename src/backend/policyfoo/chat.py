import os
import re
from typing import Optional, Dict, Union, Generator, List
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.llm.provider import llm_provider, Message
import uuid
import json

class ChatAgent:
    """Agent for generating chat responses based on policy content"""
    
    def __init__(self):
        self.PRIMARY_OPTIONS = {
            "model": os.getenv("CHAT_AGENT_MODEL", "gpt-3.5-turbo"),
            "temperature": 0.1,
            "stream": False
        }
        
        self.BACKUP_OPTIONS = {
            "model": os.getenv("BACKUP_CHAT_AGENT_MODEL", "mistral"),
            "temperature": 0.1,
            "stream": False
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
            
    def _extract_tag_content(self, xml_str: str, tag: str) -> Optional[str]:
        """Extract content between XML tags using regex"""
        try:
            pattern = f"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, xml_str, re.DOTALL)
            return match.group(1).strip() if match else None
        except Exception as e:
            logger.error(f"Error extracting {tag} tag: {str(e)}")
            return None
            
    def _format_response(self, llm_response: str) -> str:
        """Format LLM response into required XML structure"""
        try:
            # Extract content from LLM response
            answer = self._extract_tag_content(llm_response, "answer") or llm_response
            citations = self._extract_tag_content(llm_response, "citations") or ""
            follow_up = self._extract_tag_content(llm_response, "follow_up") or ""
            
            # Format into clean XML
            return f"""<response>
    <answer>{answer}</answer>
    <citations>{citations}</citations>
    <follow_up>{follow_up}</follow_up>
</response>"""
            
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return f"""<response>
    <answer>{llm_response}</answer>
    <citations></citations>
    <follow_up></follow_up>
</response>"""
            
    def _format_messages(
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
            # Replace policy content placeholder
            system_prompt = system_prompt.replace("{{POLICY_CONTENT}}", policy_content)
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
    ) -> Optional[str]:
        """Generate a response to the user's query"""
        try:
            # Format messages with conversation history
            messages = self._format_messages(query, policy_content, conversation_history)
            
            # Override temperature if provided
            if temperature is not None:
                self.PRIMARY_OPTIONS["temperature"] = temperature
                self.BACKUP_OPTIONS["temperature"] = temperature
            
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"[ChatAgent] Making LLM request for chat response")
                logger.debug(f"[ChatAgent] Query: {truncate_llm_response(query)}")
                logger.debug(f"[ChatAgent] Request ID: {request_id}")
                
            # Generate response
            response = llm_provider.generate_completion(
                prompt=query,  # Pass original query
                system_prompt=messages[0]["content"] if messages else "",  # Use the system prompt from messages
                messages=messages,  # Pass formatted messages directly
                primary_options=self.PRIMARY_OPTIONS,
                backup_options=self.BACKUP_OPTIONS,
                request_id=request_id,
                agent_name="ChatAgent"  # Add agent name to identify messages
            )
            
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"[ChatAgent] LLM response: {truncate_llm_response(response)}")
            return response
            
        except Exception as e:
            logger.error(f"[ChatAgent] Error generating chat response: {str(e)}")
            return None

# Create singleton instance
chat_agent = ChatAgent() 