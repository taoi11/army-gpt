import os
from typing import List, Optional
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.llm.provider import llm_provider, Message
import uuid

class PolicyFinder:
    """Agent for identifying relevant DOAD policies based on user queries"""
    
    def __init__(self):
        # Load model settings from environment
        self.PRIMARY_MODEL = os.getenv("POLICY_FINDER_MODEL")
        self.BACKUP_MODEL = os.getenv("BACKUP_POLICY_FINDER_MODEL")
        self.BACKUP_CTX = int(os.getenv("BACKUP_POLICY_FINDER_NUM_CTX", "1000"))
        self.BACKUP_BATCH = int(os.getenv("BACKUP_POLICY_FINDER_BATCH_SIZE", "128"))
        
        # Log model settings
        logger.debug(f"PolicyFinder initialized with models: Primary={self.PRIMARY_MODEL}, Backup={self.BACKUP_MODEL}")
        
        # LLM settings
        self.PRIMARY_OPTIONS = {
            "temperature": 0.1,
            "model": self.PRIMARY_MODEL
        }
        
        self.BACKUP_OPTIONS = {
            "temperature": 0.1,
            "model": self.BACKUP_MODEL,
            "num_ctx": self.BACKUP_CTX,
            "num_batch": self.BACKUP_BATCH
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
            
            # Load system prompt
            system_prompt = self.load_system_prompt()
            if not system_prompt:
                logger.error("Failed to load system prompt")
                return []
            
            # Log before LLM request
            logger.debug(f"Making LLM request with query: {truncate_llm_response(query)}")
            logger.debug(f"Request ID: {request_id}")
            
            # Generate policy list using LLM
            response = llm_provider.generate_completion(
                prompt=query,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                primary_options=self.PRIMARY_OPTIONS,
                backup_options=self.BACKUP_OPTIONS,
                request_id=request_id
            )
            
            # Log LLM response
            logger.debug(f"LLM response: {truncate_llm_response(response)}")
            
            if not response:
                logger.error("No response from LLM")
                return []
            
            # Parse response into list of policy numbers
            if response.lower().strip() == "none":
                return []
                
            # Split response and clean policy numbers
            policies = [
                policy.strip()
                for policy in response.split(",")
                if policy.strip()
            ]
            
            logger.info(f"Found {len(policies)} relevant policies: {policies}")
            return policies
            
        except Exception as e:
            logger.error(f"Error finding relevant policies: {str(e)}")
            logger.debug(f"Full error details: {str(e)}", exc_info=True)
            return []

# Create singleton instance
policy_finder = PolicyFinder() 