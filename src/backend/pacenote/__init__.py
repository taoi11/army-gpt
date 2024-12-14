from src.backend.utils.logger import logger
from src.backend.llm.provider import llm_provider
from src.backend.utils.monitoring import track_api_call
import os
import uuid

class PaceNoteAgent:
    """Agent for generating pace notes"""
    
    # Load model settings from environment
    PRIMARY_MODEL = os.getenv("PACE_NOTE_MODEL")
    BACKUP_MODEL = os.getenv("BACKUP_PACE_NOTE_MODEL")
    BACKUP_CTX = int(os.getenv("BACKUP_PACE_NOTE_NUM_CTX", "1000"))
    BACKUP_BATCH = int(os.getenv("BACKUP_PACE_NOTE_BATCH_SIZE", "128"))
    
    # File paths relative to /app/src
    SYSTEM_PROMPT_PATH = "prompts/pace-note.md"
    COMPETENCIES_PATH = "policies/pace-note/competency.md"
    EXAMPLES_PATH = "policies/pace-note/example_notes.md"
    
    # LLM settings from pace-note.yml
    PRIMARY_OPTIONS = {
        "temperature": 0.1,  # Default temperature from pace-note.yml
        "model": PRIMARY_MODEL
    }
    
    BACKUP_OPTIONS = {
        "temperature": 0.1,  # Default temperature from pace-note.yml
        "model": BACKUP_MODEL,
        "num_ctx": BACKUP_CTX,
        "num_batch": BACKUP_BATCH
    }
    
    @staticmethod
    def parse_competencies(content: str) -> str:
        """Parse competencies from markdown table format"""
        competencies = []
        current_competency = None
        current_facets = []
        
        for line in content.split('\n'):
            if '|' not in line or '---' in line:  # Skip header and separator lines
                continue
                
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 3:  # Skip invalid lines
                continue
                
            competency = parts[1].strip()
            facet = parts[2].strip()
            
            if competency:  # New competency
                if current_competency:  # Save previous competency
                    facets_str = "\n    - " + "\n    - ".join(current_facets)
                    competencies.append(f"- {current_competency}:{facets_str}")
                current_competency = competency
                current_facets = []
            
            if facet:  # Add facet to current competency
                current_facets.append(facet)
        
        # Add the last competency
        if current_competency:
            facets_str = "\n    - " + "\n    - ".join(current_facets)
            competencies.append(f"- {current_competency}:{facets_str}")
            
        return "\n".join(competencies)
    
    @staticmethod
    def load_system_prompt() -> str:
        """Load and format system prompt"""
        try:
            # Load system prompt template
            with open(os.path.join("/app/src", PaceNoteAgent.SYSTEM_PROMPT_PATH), "r") as f:
                system_prompt = f.read()
            
            # Load competencies
            try:
                with open(os.path.join("/app/src", PaceNoteAgent.COMPETENCIES_PATH), "r") as f:
                    competencies_content = f.read()
                competency_list = PaceNoteAgent.parse_competencies(competencies_content)
            except Exception as e:
                logger.error(f"Error loading competencies: {e}")
                competency_list = "Error loading competencies"
            
            # Load examples
            try:
                with open(os.path.join("/app/src", PaceNoteAgent.EXAMPLES_PATH), "r") as f:
                    examples = f.read()
            except Exception as e:
                logger.error(f"Error loading examples: {e}")
                examples = "Error loading examples"
            
            # Add more detailed logging for debugging only if debug is enabled
            if logger.isEnabledFor(10):  # DEBUG level
                logger.debug(f"System prompt loaded: {len(system_prompt)} chars")
                logger.debug(f"Competency list loaded: {len(competency_list)} chars")
                logger.debug(f"Examples loaded: {len(examples)} chars")
            
            return system_prompt.replace(
                "{{competency_list}}", 
                competency_list
            ).replace(
                "{{examples}}", 
                examples
            )
        except Exception as e:
            logger.error(f"Error loading system prompt: {str(e)}")
            logger.error(f"Current working directory: {os.getcwd()}")
            return None

    @staticmethod
    async def generate(content: str, temperature: float = 0.1, request_id: str = None, stream: bool = False):
        """Generate a pace note using the LLM"""
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())

            # Track API call
            track_api_call("pace_note_generate", "started")
            
            # Load system prompt
            system_prompt = PaceNoteAgent.load_system_prompt()
            if not system_prompt:
                track_api_call("pace_note_generate", "failed")
                return None
            
            # Update temperature in options
            primary_options = PaceNoteAgent.PRIMARY_OPTIONS.copy()
            primary_options["temperature"] = temperature
            
            backup_options = PaceNoteAgent.BACKUP_OPTIONS.copy()
            backup_options["temperature"] = temperature
                
            # Generate note using LLM with tool-specific options
            response = await llm_provider.generate_completion(
                prompt=content,
                system_prompt=system_prompt,
                primary_options=primary_options,
                backup_options=backup_options,
                request_id=request_id,
                stream=stream,
                agent_name="PaceNoteAgent"  # Add agent name to identify messages
            )
            
            if stream:
                async def stream_response():
                    try:
                        async for chunk in response:
                            yield chunk
                        track_api_call("pace_note_generate", "success")
                    except Exception as e:
                        logger.error(f"[PaceNoteAgent] Error in streaming response: {e}")
                        track_api_call("pace_note_generate", "failed")
                return stream_response()
            
            # Only track success if we got a response
            if response:
                track_api_call("pace_note_generate", "success")
            else:
                track_api_call("pace_note_generate", "failed")
                
            return response
            
        except Exception as e:
            logger.error(f"[PaceNoteAgent] Error generating pace note: {e}")
            track_api_call("pace_note_generate", "failed")
            return None

# Create singleton instance
pace_note_agent = PaceNoteAgent() 