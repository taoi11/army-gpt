import os
import re
from typing import Optional, Dict, Union, Generator, List
from src.backend.utils.logger import logger
from src.backend.llm.provider import llm_provider, Message
import uuid

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
            
    async def generate_response(
        self,
        query: str,
        policy_content: str,
        request_id: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Union[str, Generator[str, None, None]]:
        """Generate a response based on policy content"""
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
                
            # Load system prompt
            system_prompt = self.load_system_prompt()
            if not system_prompt:
                return "Error: Failed to load system prompt"
                
            # Override temperature if provided
            if temperature is not None:
                self.PRIMARY_OPTIONS["temperature"] = temperature
                self.BACKUP_OPTIONS["temperature"] = temperature
            
            # Replace placeholder in system prompt with raw policy content
            system_prompt = system_prompt.replace("{{POLICY_DATA}}", policy_content)
            
            # Generate response
            response = llm_provider.generate_completion(
                prompt=query,
                system_prompt=system_prompt,
                primary_options=self.PRIMARY_OPTIONS,
                backup_options=self.BACKUP_OPTIONS,
                request_id=request_id
            )
            
            # Format response for frontend
            formatted_response = self._format_response(response)
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return f"""<response>
    <answer>Error generating response: {str(e)}</answer>
    <citations></citations>
    <follow_up></follow_up>
</response>"""

# Create singleton instance
chat_agent = ChatAgent() 