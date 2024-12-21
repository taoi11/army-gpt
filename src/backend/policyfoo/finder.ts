import { BaseAgent } from './base.js';
import { PolicyReference, PolicyError, PolicyAgentOptions } from './types.js';
import { config, ModelConfig } from '../config.js';
import { logger } from '../utils/logger.js';

export class PolicyFinder extends BaseAgent {
  constructor() {
    super('PolicyFinder');
  }

  protected getPromptFileName(): string {
    return 'policyFinder';
  }

  protected getLLMConfig(isBackup: boolean): ModelConfig['primary'] | ModelConfig['backup'] {
    return isBackup ? config.policy.finder.backup : config.policy.finder.primary;
  }

  async search(query: string, options: PolicyAgentOptions = {}): Promise<PolicyReference[]> {
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