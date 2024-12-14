import logging
import sys
import os
from typing import Any

def truncate_llm_response(response: Any, head_tail_length: int = 100) -> str:
    """Truncate LLM response for debug logging, showing both start and end of the response"""
    if not response:
        return str(response)
        
    # Convert response to string if it's not already
    response_str = str(response)
        
    if len(response_str) <= head_tail_length * 2:
        return response_str
        
    head = response_str[:head_tail_length]
    tail = response_str[-head_tail_length:]
    middle_length = len(response_str) - (head_tail_length * 2)
    
    return f"{head}... [{middle_length} chars truncated] ...{tail}"

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