import os
import requests
from src.backend.utils.logger import logger
from apscheduler.schedulers.background import BackgroundScheduler

class OpenRouterCreditsChecker:
    """Manages OpenRouter API credits checking"""
    
    def __init__(self):
        self.credits_available = True
        self.scheduler = None
        
    def check_credits(self):
        """Check if we have credits available on OpenRouter"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        
        if not api_key:
            logger.error("OPENROUTER_API_KEY not found")
            self.credits_available = False
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
                self.credits_available = False
                return False
                
            self.credits_available = True
            return True
            
        except Exception as e:
            logger.error(f"Error checking OpenRouter credits: {str(e)}")
            self.credits_available = False
            return False
    
    def start(self):
        """Start the credits checker"""
        logger.info("Running initial OpenRouter credits check")
        self.check_credits()
        
        # Setup scheduler for periodic checks
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self.check_credits, 'interval', minutes=5, id='credits_check')
        self.scheduler.start()
        
        logger.info("OpenRouter credits check scheduler started")
    
    def stop(self):
        """Stop the credits checker"""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("OpenRouter credits check scheduler stopped")
    
    @property
    def has_credits(self):
        """Check if credits are available"""
        return self.credits_available

# Create a global instance
credits_checker = OpenRouterCreditsChecker() 