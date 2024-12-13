import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import app and logger
from src.backend.utils.web import app
from src.backend.utils.logger import logger

# Import middleware
from src.backend.utils.rate_limit import RateLimitMiddleware, rate_limiter
from src.backend.utils.monitoring import MetricsMiddleware

# Import routers
from src.backend.utils.web import router as web_router
from src.backend.llm.routes import router as llm_router

# Import credits checker
from src.backend.llm.keycheck import credits_checker

# Server configuration
WORKERS = int(os.getenv("WORKERS", "1"))
LOG_LEVEL = "debug" if os.getenv("DEBUG_MODE", "false").lower() == "true" else "info"

# Environment checks
def check_environment():
    """Check required environment variables and set defaults"""
    
    # Check required variables
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("OPENROUTER_API_KEY not found in environment")
        exit(1)
        
    if not os.getenv("JWT_SECRET"):
        logger.error("JWT_SECRET not set in environment")
        exit(1)
    
    # Check optional variables with defaults
    if not os.getenv("LLM_BASE_URL"):
        logger.warning("LLM_BASE_URL not set, using default OpenRouter URL")
        
    if not os.getenv("PACE_MODEL"):
        logger.warning("PACE_MODEL not set, model selection may fail")
    
    # Set rate limit defaults
    os.environ.setdefault("RATE_LIMIT_PER_HOUR", "15")
    os.environ.setdefault("RATE_LIMIT_PER_DAY", "50")

def setup_middleware():
    """Setup FastAPI middleware"""
    # Connect credits checker to rate limiter
    rate_limiter.set_credits_check(lambda: credits_checker.has_credits)
    
    # Add middleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(MetricsMiddleware)

def setup_routers():
    """Setup FastAPI routers"""
    app.include_router(web_router)
    app.include_router(llm_router)

def log_startup_info():
    """Log startup configuration"""
    logger.info("Starting Army-GPT server")
    logger.info(f"Debug mode: {os.getenv('DEBUG_MODE', 'false')}")
    logger.info(f"Rate limits: {os.getenv('RATE_LIMIT_PER_HOUR')}/hour, {os.getenv('RATE_LIMIT_PER_DAY')}/day")
    logger.info(f"Primary LLM: {os.getenv('LLM_BASE_URL')} using model {os.getenv('PACE_MODEL')}")
    logger.info(f"Backup LLM: {os.getenv('BACKUP_LLM_BASE_URL')} using model {os.getenv('BACKUP_PACE_MODEL')}")

def main():
    """Main entry point for the application"""
    check_environment()
    setup_middleware()
    setup_routers()
    
    # Start credits checker
    credits_checker.start()
    
    if __name__ == "__main__":
        import uvicorn
        
        log_startup_info()
        
        uvicorn.run(
            "src.backend.main:app",
            host="0.0.0.0",  # Required for Docker
            port=8020,       # Match Docker port
            workers=WORKERS,
            log_level=LOG_LEVEL,
            reload=os.getenv("DEBUG_MODE", "false").lower() == "true",  # Only reload in debug mode
            access_log=True
        )

# Initialize application
main() 