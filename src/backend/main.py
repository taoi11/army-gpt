import os
from dotenv import load_dotenv
from src.backend.llm import app
from src.backend.utils.logger import logger

# Load environment variables
load_dotenv()

# Server configuration
WORKERS = int(os.getenv("WORKERS", "1"))
LOG_LEVEL = "debug" if os.getenv("DEBUG_MODE", "false").lower() == "true" else "info"

# LLM configuration check
if not os.getenv("OPENROUTER_API_KEY"):
    logger.error("OPENROUTER_API_KEY not found in environment")
    exit(1)

if not os.getenv("LLM_BASE_URL"):
    logger.warning("LLM_BASE_URL not set, using default OpenRouter URL")

if not os.getenv("PACE_MODEL"):
    logger.warning("PACE_MODEL not set, model selection may fail")

# JWT configuration check
if not os.getenv("JWT_SECRET"):
    logger.error("JWT_SECRET not set in environment")
    exit(1)

# Import keycheck to ensure it runs on startup
import src.backend.llm.keycheck

# Rate limit configuration (these will be picked up by the rate limiter)
os.environ.setdefault("RATE_LIMIT_PER_HOUR", "15")
os.environ.setdefault("RATE_LIMIT_PER_DAY", "50")

if __name__ == "__main__":
    import uvicorn
    
    # Log startup configuration
    logger.info("Starting Army-GPT server")
    logger.info(f"Debug mode: {os.getenv('DEBUG_MODE', 'false')}")
    logger.info(f"Rate limits: {os.getenv('RATE_LIMIT_PER_HOUR')}/hour, {os.getenv('RATE_LIMIT_PER_DAY')}/day")
    logger.info(f"Primary LLM: {os.getenv('LLM_BASE_URL')} using model {os.getenv('PACE_MODEL')}")
    logger.info(f"Backup LLM: {os.getenv('BACKUP_LLM_BASE_URL')} using model {os.getenv('BACKUP_PACE_MODEL')}")
    
    uvicorn.run(
        "src.backend.main:app",
        host="0.0.0.0",  # Required for Docker
        port=8020,       # Match Docker port
        workers=WORKERS,
        log_level=LOG_LEVEL,
        reload=os.getenv("DEBUG_MODE", "false").lower() == "true",  # Only reload in debug mode
        access_log=True
    ) 