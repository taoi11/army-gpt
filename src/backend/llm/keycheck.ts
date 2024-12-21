import axios from 'axios';
import { config } from '../config.js';
import { logger } from '../utils/logger.js';

class OpenRouterCreditsChecker {
  private creditsAvailable: boolean = true;
  private checkInterval: NodeJS.Timeout | null = null;
  private readonly CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes in milliseconds
  private creditsChangeCallback: ((hasCredits: boolean) => void) | null = null;

  async checkCredits(): Promise<boolean> {
    if (!config.llm.primary.apiKey) {
      logger.error('OPENROUTER_API_KEY not found');
      this.updateCreditsState(false);
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
        this.updateCreditsState(false);
        return false;
      }

      this.updateCreditsState(true);
      return true;

    } catch (error) {
      logger.error('Error checking OpenRouter credits:', error);
      this.updateCreditsState(false);
      return false;
    }
  }

  private updateCreditsState(newState: boolean): void {
    if (this.creditsAvailable !== newState) {
      this.creditsAvailable = newState;
      if (this.creditsChangeCallback) {
        this.creditsChangeCallback(newState);
      }
    }
  }

  onCreditsChange(callback: (hasCredits: boolean) => void): void {
    this.creditsChangeCallback = callback;
    // Immediately call with current state
    callback(this.creditsAvailable);
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