import os
import asyncio
from typing import List, Dict, Optional
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.llm.provider import llm_provider, Message
import uuid
import json

class PolicyReader:
    """Agent for extracting relevant content from policies"""
    
    def __init__(self):
        self.PRIMARY_OPTIONS = {
            "model": os.getenv("POLICY_READER_MODEL"),
            "temperature": 0.1,
            "parallel": True  # Primary LLM can handle parallel requests
        }
        
        self.BACKUP_OPTIONS = {
            "model": os.getenv("BACKUP_POLICY_READER_MODEL"),
            "temperature": 0.1,
            "parallel": False,  # Backup LLM should process sequentially
            "num_ctx": int(os.getenv("BACKUP_POLICY_READER_NUM_CTX")),
            "num_batch": int(os.getenv("BACKUP_POLICY_READER_BATCH_SIZE"))
        }
        
        # Parallel execution settings
        self.STAGGER_DELAY = 0.25  # 250ms between parallel requests
        self.TIMEOUT = 35.0  # 35s timeout for parallel execution
        
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

    async def extract_policy_content(
        self,
        policy_number: str,
        query: str,
        request_id: str,
        conversation_history: Optional[List[Message]] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """Extract relevant content from a single policy"""
        try:
            # Load policy content
            policy_content = self.load_policy_content(policy_number)
            if not policy_content:
                return None
                
            # Format messages with conversation history
            messages = self._format_messages(query, policy_content, conversation_history)
            
            # Create copies of options to avoid modifying class-level dictionaries
            primary_options = self.PRIMARY_OPTIONS.copy()
            backup_options = self.BACKUP_OPTIONS.copy()
            
            # Override temperature if provided
            if temperature is not None:
                primary_options["temperature"] = temperature
                backup_options["temperature"] = temperature
            
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"[PolicyReader] Making LLM request for policy {policy_number}")
                logger.debug(f"[PolicyReader] Query: {truncate_llm_response(query)}")
                logger.debug(f"[PolicyReader] Request ID: {request_id}")
                
            # Generate response
            response = await llm_provider.generate_completion(
                prompt=query,  # Pass original query
                system_prompt=messages[0]["content"] if messages else "",  # Use the system prompt from messages
                messages=messages,  # Pass formatted messages directly
                primary_options=primary_options,
                backup_options=backup_options,
                request_id=request_id,
                agent_name="PolicyReader"  # Add agent name to identify messages
            )
            
            # Log response at debug level only
            if response and logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"[PolicyReader] Policy {policy_number} response: {truncate_llm_response(response)}")
            return response
            
        except Exception as e:
            logger.error(f"[PolicyReader] Error extracting policy content: {str(e)}")
            return None
            
    async def get_policy_content(
        self,
        policy_numbers: List[str],
        query: str,
        request_id: Optional[str] = None,
        conversation_history: Optional[List[Message]] = None,
        temperature: Optional[float] = None,
        parallel: bool = True  # This will be overridden by options
    ) -> Dict[str, str]:
        """Get content from multiple policies with parallel or sequential processing"""
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
                
            results = {}
            if not policy_numbers:
                return results

            # Create copies of options
            primary_options = self.PRIMARY_OPTIONS.copy()
            backup_options = self.BACKUP_OPTIONS.copy()
            
            # Override temperature if provided
            if temperature is not None:
                primary_options["temperature"] = temperature
                backup_options["temperature"] = temperature

            # Try first policy to determine which options we're using
            first_result = await self.extract_policy_content(
                policy_number=policy_numbers[0],
                query=query,
                request_id=f"{request_id}-{policy_numbers[0]}",
                conversation_history=conversation_history,
                temperature=temperature
            )
            
            # Store first result if valid
            if first_result is not None:
                results[policy_numbers[0]] = first_result

            # Get the options being used (based on whether primary LLM succeeded)
            current_options = primary_options if first_result is not None else backup_options
            use_parallel = current_options.get("parallel", False)
            
            # Process remaining policies
            remaining_policies = policy_numbers[1:]
            if not remaining_policies:
                return results

            if use_parallel:
                logger.debug("[PolicyReader] Using parallel processing")
                # Create tasks for remaining policies
                tasks = []
                for i, policy_number in enumerate(remaining_policies):
                    await asyncio.sleep(self.STAGGER_DELAY * i)
                    task = asyncio.create_task(self.extract_policy_content(
                        policy_number=policy_number,
                        query=query,
                        request_id=f"{request_id}-{policy_number}",
                        conversation_history=conversation_history,
                        temperature=temperature
                    ))
                    tasks.append((policy_number, task))
                
                # Wait for all tasks with timeout
                try:
                    async with asyncio.timeout(self.TIMEOUT):
                        for policy_number, task in tasks:
                            try:
                                result = await task
                                if result is not None:
                                    results[policy_number] = result
                            except Exception as e:
                                logger.error(f"Error processing policy {policy_number}: {e}")
                                continue
                except asyncio.TimeoutError:
                    logger.error("Parallel policy extraction timed out")
                    # Cancel any remaining tasks
                    for _, task in tasks:
                        if not task.done():
                            task.cancel()
            else:
                logger.debug("[PolicyReader] Using sequential processing")
                # Sequential execution
                for policy_number in remaining_policies:
                    try:
                        result = await self.extract_policy_content(
                            policy_number=policy_number,
                            query=query,
                            request_id=f"{request_id}-{policy_number}",
                            conversation_history=conversation_history,
                            temperature=temperature
                        )
                        if result is not None:
                            results[policy_number] = result
                    except Exception as e:
                        logger.error(f"Error processing policy {policy_number}: {e}")
                        continue
            
            return results
                
        except Exception as e:
            logger.error(f"Error getting policy content: {str(e)}")
            return {}

# Create singleton instance
policy_reader = PolicyReader() 