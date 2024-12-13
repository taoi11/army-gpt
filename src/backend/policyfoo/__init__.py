from src.backend.policyfoo.finder import policy_finder
from src.backend.policyfoo.chat import chat_agent
from src.backend.utils.logger import logger

def init_app() -> None:
    """Initialize the policy finder module"""
    try:
        # Log successful initialization
        logger.info("PolicyFinder module initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize PolicyFinder module: {str(e)}")
        raise

__all__ = ["policy_finder", "chat_agent", "init_app"] 