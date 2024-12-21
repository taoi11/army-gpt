import { BaseAgent } from './base';
import { PolicyReference, PolicyError } from './types';
import { config } from '../config';
import { logger } from '../utils/logger';

export class PolicyFinder extends BaseAgent {
  constructor() {
    super('PolicyFinder');
  }

  protected getPromptFileName(): string {
    return 'policy-finder';
  }

  protected getLLMConfig(isBackup: boolean): any {
    return isBackup ? config.policy.finder.backup : config.policy.finder.primary;
  }

  async search(query: string, options: any = {}): Promise<PolicyReference[]> {
    try {
      const response = await this.generateSync(
        query,
        this.systemPrompt,
        undefined,
        options
      );

      // Parse response and validate
      try {
        const results = JSON.parse(response) as PolicyReference[];
        if (!Array.isArray(results)) {
          throw new Error('Invalid response format');
        }
        return results;
      } catch (e) {
        logger.error('[PolicyFinder] Failed to parse response:', e);
        throw new PolicyError(
          'Failed to parse search results',
          'FINDER_ERROR',
          e
        );
      }
    } catch (error) {
      if (error instanceof PolicyError) {
        throw error;
      }
      logger.error('[PolicyFinder] Search error:', error);
      throw new PolicyError(
        'Policy search failed',
        'FINDER_ERROR',
        error
      );
    }
  }
} 