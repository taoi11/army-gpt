from src.backend.utils.logger import logger
from src.backend.llm.provider import llm_provider
from src.backend.utils.monitoring import track_api_call

class PaceNoteAgent:
    """Agent for generating pace notes"""
    
    @staticmethod
    def load_system_prompt() -> str:
        """Load and format system prompt"""
        try:
            # Load system prompt template
            with open("src/prompts/pace-note.md", "r") as f:
                system_prompt = f.read()
                
            # TODO: Load competencies and examples from policy documents
            # For now using placeholders until policy documents are set up
            return system_prompt.replace(
                "{{competency_list}}", 
                "- Leadership\n- Initiative\n- Problem Solving"
            ).replace(
                "{{examples}}", 
                "Example 1: The member demonstrated leadership during a training exercise.\n" +
                "Example 2: Through effective communication, tasks were completed efficiently."
            )
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return None

    @staticmethod
    def generate(content: str, temperature: float = 0.1) -> str:
        """Generate a pace note using the LLM"""
        try:
            # Track API call
            track_api_call("pace_note_generate", "started")
            
            # Load system prompt
            system_prompt = PaceNoteAgent.load_system_prompt()
            if not system_prompt:
                track_api_call("pace_note_generate", "failed")
                return None
                
            # Generate note using LLM
            note = llm_provider.generate_completion(
                prompt=content,
                system_prompt=system_prompt,
                temperature=temperature
            )
            
            if note:
                track_api_call("pace_note_generate", "success")
            else:
                track_api_call("pace_note_generate", "failed")
                
            return note
            
        except Exception as e:
            logger.error(f"Error generating pace note: {str(e)}")
            track_api_call("pace_note_generate", "error")
            raise

# Create singleton instance
pace_note_agent = PaceNoteAgent() 