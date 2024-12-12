from src.backend.utils.logger import logger
from src.backend.llm.provider import llm_provider
from src.backend.utils.monitoring import track_api_call
import uuid

class PaceNoteAgent:
    """Agent for generating pace notes"""
    
    # LLM settings
    PRIMARY_OPTIONS = {
        "temperature": 0.1  # Default temperature
    }
    
    BACKUP_OPTIONS = {
        "temperature": 0.1,  # Default temperature
        "num_ctx": 14336,    # Context window size
        "num_batch": 256     # Batch size for processing
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
            with open("src/prompts/pace-note.md", "r") as f:
                system_prompt = f.read()
            
            # Load competencies from policy file
            try:
                with open("src/policies/pace-note/competency.md", "r") as f:
                    competencies_content = f.read()
                competency_list = PaceNoteAgent.parse_competencies(competencies_content)
            except Exception as e:
                logger.error(f"Error loading competencies: {e}")
                competency_list = "Error loading competencies"
            
            # Load examples from policy file - pass through raw content
            try:
                with open("src/policies/pace-note/example_notes.md", "r") as f:
                    examples = f.read()
            except Exception as e:
                logger.error(f"Error loading examples: {e}")
                examples = "Error loading examples"
            
            return system_prompt.replace(
                "{{competency_list}}", 
                competency_list
            ).replace(
                "{{examples}}", 
                examples
            )
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return None

    @staticmethod
    def generate(content: str, temperature: float = 0.1, request_id: str = None) -> str:
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
            note = llm_provider.generate_completion(
                prompt=content,
                system_prompt=system_prompt,
                primary_options=primary_options,
                backup_options=backup_options,
                request_id=request_id
            )
            
            if note:
                track_api_call("pace_note_generate", "success")
            else:
                track_api_call("pace_note_generate", "failed")
                
            return note
            
        except Exception as e:
            logger.error(f"Error generating pace note: {str(e)}")
            track_api_call("pace_note_generate", "failed")
            return None

# Create singleton instance
pace_note_agent = PaceNoteAgent() 