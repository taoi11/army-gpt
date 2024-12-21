import axios from 'axios';
import { config } from '../config';
import { logger } from '../utils/logger';

class OpenRouterCreditsChecker {
  private creditsAvailable: boolean = true;
  private checkInterval: NodeJS.Timer | null = null;
  private readonly CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes in milliseconds

  async checkCredits(): Promise<boolean> {
    if (!config.llm.primary.apiKey) {
      logger.error('OPENROUTER_API_KEY not found');
      this.creditsAvailable = false;
      return false;
    }

    try {
      const response = await axios.get(
        `${config.llm.primary.baseUrl}/auth/key`,
        {
          headers: {
            'Authorization': `Bearer ${config.llm.primary.apiKey}`
          },
          timeout: 5000 // 5 seconds
        }
      );

      // If we get any error response, we're out of credits
      if (response.status !== 200) {
        logger.warn(`OpenRouter credits check failed: ${response.status}`);
        this.creditsAvailable = false;
        return false;
      }

      this.creditsAvailable = true;
      return true;

    } catch (error) {
      logger.error('Error checking OpenRouter credits:', error);
      this.creditsAvailable = false;
      return false;
    }
  }

  start(): void {
    logger.info('Running initial OpenRouter credits check');
    this.checkCredits();

    // Setup interval for periodic checks
    this.checkInterval = setInterval(
      () => this.checkCredits(),
      this.CHECK_INTERVAL
    );

    logger.info('OpenRouter credits check scheduler started');
  }

  stop(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
      logger.info('OpenRouter credits check scheduler stopped');
    }
  }

  get hasCredits(): boolean {
    return this.creditsAvailable;
  }
}

// Create a global instance
export const creditsChecker = new OpenRouterCreditsChecker(); 