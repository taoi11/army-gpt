import os
from typing import List, Optional, Dict
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.llm.provider import llm_provider, Message
import uuid
import json
import re

class PolicyFinder:
    """Agent for identifying relevant DOAD policies based on user queries"""
    
    def __init__(self):
        # Load model settings from environment
        self.PRIMARY_MODEL = os.getenv("POLICY_FINDER_MODEL")
        self.BACKUP_MODEL = os.getenv("BACKUP_POLICY_FINDER_MODEL")
        self.BACKUP_CTX = int(os.getenv("BACKUP_POLICY_FINDER_NUM_CTX"))
        self.BACKUP_BATCH = int(os.getenv("BACKUP_POLICY_FINDER_BATCH_SIZE"))
        
        # Log model settings
        logger.debug(f"PolicyFinder initialized with models: Primary={self.PRIMARY_MODEL}, Backup={self.BACKUP_MODEL}")
        
        # LLM settings
        self.PRIMARY_OPTIONS = {
            "temperature": 0.1,
            "model": self.PRIMARY_MODEL,
            "stream": True
        }
        
        self.BACKUP_OPTIONS = {
            "temperature": 0.1,
            "model": self.BACKUP_MODEL,
            "num_ctx": self.BACKUP_CTX,
            "num_batch": self.BACKUP_BATCH,
            "stream": True
        }
        
        # Log options
        logger.debug(f"PolicyFinder options: Primary={self.PRIMARY_OPTIONS}, Backup={self.BACKUP_OPTIONS}")
    
    def load_system_prompt(self) -> Optional[str]:
        """Load the system prompt for policy finding"""
        try:
            prompt_path = os.path.join("src", "prompts", "policyFinder.md")
            if not os.path.exists(prompt_path):
                logger.error(f"System prompt not found at {prompt_path}")
                return None
                
            # Load system prompt template
            with open(prompt_path, 'r') as f:
                system_prompt = f.read().strip()
                
            # Load DOAD list table
            doad_list_path = os.path.join("src", "policies", "doad", "DOAD-list-table.md")
            try:
                with open(doad_list_path, 'r') as f:
                    doad_list = f.read().strip()
            except Exception as e:
                logger.error(f"Error loading DOAD list: {str(e)}")
                return None
                
            # Log loaded content lengths
            logger.debug(f"Loaded system prompt ({len(system_prompt)} chars)")
                
            # Replace placeholder in system prompt
            return system_prompt.replace("{{DOAD_LIST_TABLE}}", doad_list)
                
        except Exception as e:
            logger.error(f"Error loading system prompt: {str(e)}")
            return None

    def _format_messages(
        self,
        query: str,
        conversation_history: Optional[List[Message]] = None
    ) -> List[Dict[str, str]]:
        """Format conversation history into messages for the LLM API"""
        messages = []
        
        # Add system prompt first
        system_prompt = self.load_system_prompt()
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history if available
        if conversation_history:
            # Get last 2 exchanges (4 messages), excluding the current query
            history = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
            
            # Add each message with its role
            for msg in history:
                # Skip if this message matches our current query
                if msg.role == "user" and msg.content.strip() == query.strip():
                    continue
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add the current query as the final user message
        messages.append({
            "role": "user",
            "content": query
        })
        
        return messages

    async def find_relevant_policies(
        self,
        query: str,
        conversation_history: Optional[List[Message]] = None,
        request_id: str = None
    ) -> List[str]:
        """Find relevant DOAD policies for a given query"""
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
            
            # Format messages with conversation history
            messages = self._format_messages(query, conversation_history)
            
            # Get the user's message from formatted messages
            user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), query)
            
            # Generate policy list using LLM
            response = await llm_provider.generate_completion(
                prompt=user_message,  # Use the formatted user message
                system_prompt=messages[0]["content"] if messages else "",  # Use the system prompt from messages
                messages=messages,  # Pass formatted messages directly
                primary_options=self.PRIMARY_OPTIONS,
                backup_options=self.BACKUP_OPTIONS,
                request_id=request_id,
                agent_name="PolicyFinder"  # Add agent name to identify messages
            )
            
            # Handle streaming response
            if hasattr(response, '__aiter__'):
                full_response = ''
                async for chunk in response:
                    if chunk:
                        full_response += chunk
                response = full_response
            
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"[PolicyFinder] LLM response: {truncate_llm_response(response)}")
            
            if not response:
                logger.error("[PolicyFinder] No response from LLM")
                return []
            
            # Parse response into list of policy numbers
            if response.lower().strip() == "none":
                return []
                
            # Split response and clean policy numbers
            # First, try to extract policy numbers using a more strict pattern
            policy_numbers = re.findall(r'\b\d{4}-\d+\b', response)
            
            # If no policy numbers found with strict pattern, fall back to comma split
            if not policy_numbers:
                policies = [
                    policy.strip()
                    for policy in response.split(",")
                    if policy.strip() and re.match(r'\d{4}-\d+', policy.strip())
                ]
                policy_numbers = policies
            
            # If no policies found but we have context, try again without context
            if not policy_numbers and conversation_history:
                logger.debug("[PolicyFinder] No policies found with context, trying without context")
                return await self.find_relevant_policies(query=query, request_id=request_id)
            
            # Always log found policies at INFO level
            if policy_numbers:
                logger.info(f"[PolicyFinder] Found {len(policy_numbers)} relevant policies: {policy_numbers}")
            
            return policy_numbers
            
        except Exception as e:
            logger.error(f"[PolicyFinder] Error finding relevant policies: {str(e)}")
            logger.debug(f"[PolicyFinder] Full error details: {str(e)}", exc_info=True)
            return []

# Create singleton instance
policy_finder = PolicyFinder() 