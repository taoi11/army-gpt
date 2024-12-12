import os
import requests
from src.backend.utils.logger import logger

# Global variable to track credit status
CREDITS_AVAILABLE = True

def check_credits():
    """Check if we have credits available on OpenRouter"""
    global CREDITS_AVAILABLE
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    
    if not api_key:
        logger.error("OPENROUTER_API_KEY not found")
        CREDITS_AVAILABLE = False
        return False
        
    try:
        response = requests.get(
            f"{base_url}/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5.0
        )
        
        # If we get a 401 or any error response, we're out of credits
        if response.status_code != 200:
            logger.warning(f"OpenRouter credits check failed: {response.status_code}")
            CREDITS_AVAILABLE = False
            return False
            
        CREDITS_AVAILABLE = True
        return True
        
    except Exception as e:
        logger.error(f"Error checking OpenRouter credits: {str(e)}")
        CREDITS_AVAILABLE = False
        return False

# Run initial check on module import
logger.info("Running initial OpenRouter credits check")
check_credits()

# Setup scheduler for periodic checks
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(check_credits, 'interval', minutes=5, id='credits_check')
scheduler.start()

logger.info("OpenRouter credits check scheduler started") 