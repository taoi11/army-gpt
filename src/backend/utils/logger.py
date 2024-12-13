import logging
import sys
import os
from typing import Any

def truncate_llm_response(response: str, max_length: int = 500) -> str:
    """Truncate LLM response for debug logging"""
    if not response or len(response) <= max_length:
        return response
    return f"{response[:max_length]}... [truncated {len(response)-max_length} chars]"

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with console handler"""
    logger = logging.getLogger(name)
    
    # Set log level based on DEBUG_MODE environment variable
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    # Format for console output
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Create main logger instance
logger = setup_logger('army-gpt') 