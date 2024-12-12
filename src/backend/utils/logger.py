import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with console handler"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

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