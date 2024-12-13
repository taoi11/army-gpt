import os
import asyncio
from typing import List, Dict, Optional
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.llm.provider import llm_provider, Message
import uuid

class PolicyReader:
    """Agent for extracting relevant content from policies"""
    
    def __init__(self):
        self.PRIMARY_OPTIONS = {
            "model": os.getenv("POLICY_READER_MODEL", "gpt-3.5-turbo"),
            "temperature": 0.1,
            "stream": False
        }
        
        self.BACKUP_OPTIONS = {
            "model": os.getenv("BACKUP_POLICY_READER_MODEL", "mistral"),
            "temperature": 0.1,
            "stream": False
        }
        
        # Parallel execution settings
        self.STAGGER_DELAY = 0.25  # 250ms between parallel requests
        self.TIMEOUT = 35.0  # 35s timeout for parallel execution (slightly longer than primary LLM timeout)
        
        logger.debug(f"PolicyReader initialized with options: Primary={self.PRIMARY_OPTIONS}, Backup={self.BACKUP_OPTIONS}")
        
    def load_system_prompt(self) -> Optional[str]:
        """Load the system prompt for policy reading"""
        try:
            prompt_path = os.path.join("src", "prompts", "policyReader.md")
            if not os.path.exists(prompt_path):
                logger.error(f"System prompt not found at {prompt_path}")
                return None
                
            with open(prompt_path, 'r') as f:
                system_prompt = f.read().strip()
                logger.debug(f"Loaded system prompt ({len(system_prompt)} chars)")
                return system_prompt
                
        except Exception as e:
            logger.error(f"Error loading system prompt: {str(e)}")
            return None
            
    def load_policy_content(self, policy_number: str) -> Optional[str]:
        """Load content of a specific policy"""
        try:
            # Construct policy path
            policy_path = os.path.join("src", "policies", "doad", f"{policy_number}.md")
            logger.debug(f"Loading policy {policy_number} from: {policy_path}")
            
            if not os.path.exists(policy_path):
                logger.error(f"Policy file not found: {policy_path}")
                return None
                
            with open(policy_path, 'r') as f:
                content = f.read().strip()
                logger.debug(f"Successfully loaded policy {policy_number} ({len(content)} chars)")
                return content
                
        except Exception as e:
            logger.error(f"Error loading policy {policy_number}: {str(e)}")
            logger.debug(f"Full error details:", exc_info=True)
            return None
            
    async def extract_policy_content(
        self,
        policy_number: str,
        query: str,
        request_id: str,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """Extract relevant content from a single policy"""
        try:
            # Load system prompt
            system_prompt = self.load_system_prompt()
            if not system_prompt:
                return None
                
            # Load policy content
            policy_content = self.load_policy_content(policy_number)
            if not policy_content:
                return None
                
            # Replace placeholder in system prompt with policy content
            system_prompt = system_prompt.replace("{{POLICY_CONTENT}}", policy_content)
            
            # Override temperature if provided
            if temperature is not None:
                self.PRIMARY_OPTIONS["temperature"] = temperature
                self.BACKUP_OPTIONS["temperature"] = temperature
            
            logger.debug(f"Making LLM request for policy {policy_number}")
            logger.debug(f"Query: {truncate_llm_response(query)}")
            logger.debug(f"Request ID: {request_id}")
                
            # Generate response
            response = llm_provider.generate_completion(
                prompt=query,
                system_prompt=system_prompt,
                primary_options=self.PRIMARY_OPTIONS,
                backup_options=self.BACKUP_OPTIONS,
                request_id=request_id
            )
            
            logger.debug(f"LLM response for policy {policy_number}: {truncate_llm_response(response)}")
            return response
            
        except Exception as e:
            logger.error(f"Error extracting policy content: {str(e)}")
            return None
            
    async def get_policy_content(
        self,
        policy_numbers: List[str],
        query: str,
        request_id: Optional[str] = None,
        temperature: Optional[float] = None,
        parallel: bool = True
    ) -> Dict[str, str]:
        """Get content from multiple policies with parallel or sequential processing"""
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
                
            # Create tasks for each policy
            tasks = []
            for i, policy_number in enumerate(policy_numbers):
                task = self.extract_policy_content(
                    policy_number=policy_number,
                    query=query,
                    request_id=f"{request_id}-{policy_number}",
                    temperature=temperature
                )
                
                if parallel:
                    # Add stagger delay for parallel execution
                    await asyncio.sleep(self.STAGGER_DELAY * i)
                    tasks.append(asyncio.create_task(task))
                else:
                    # Sequential execution
                    result = await task
                    if result:
                        tasks.append(result)
                        
            if parallel:
                # Wait for all tasks with timeout
                try:
                    async with asyncio.timeout(self.TIMEOUT):
                        results = await asyncio.gather(*tasks)
                    return {
                        policy_number: result 
                        for policy_number, result in zip(policy_numbers, results)
                        if result is not None
                    }
                except asyncio.TimeoutError:
                    logger.error("Parallel policy extraction timed out")
                    # Cancel any remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    return {}
            else:
                # Return sequential results
                return {
                    policy_number: result
                    for policy_number, result in zip(policy_numbers, tasks)
                    if result is not None
                }
                
        except Exception as e:
            logger.error(f"Error getting policy content: {str(e)}")
            return {}

# Create singleton instance
policy_reader = PolicyReader() 