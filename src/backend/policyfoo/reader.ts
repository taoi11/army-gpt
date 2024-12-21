import { BaseAgent } from './base.js';
import { PolicyContent, PolicyError, PolicyAgentOptions } from './types.js';
import { config, ModelConfig } from '../config.js';
import { logger } from '../utils/logger.js';

export class PolicyReader extends BaseAgent {
  constructor() {
    super('PolicyReader');
  }

  protected getPromptFileName(): string {
    return 'policyReader';
  }

  protected getLLMConfig(isBackup: boolean): ModelConfig['primary'] | ModelConfig['backup'] {
    return isBackup ? config.policy.reader.backup : config.policy.reader.primary;
  }

  async read(policyNumber: string, section: string, options: PolicyAgentOptions = {}): Promise<PolicyContent> {
    try {
      const response = await this.generateSync(
        JSON.stringify({ policyNumber, section }),
        this.systemPrompt,
        undefined,
        options
      );

      // Parse response and validate
      try {
        const content = JSON.parse(response) as PolicyContent;
        if (!content.policyNumber || !content.section || !content.content) {
          throw new Error('Invalid response format');
        }
        return content;
      } catch (e) {
        logger.error('[PolicyReader] Failed to parse response:', e);
        throw new PolicyError(
          'Failed to parse policy content',
          'READER_ERROR',
          e
        );
      }
    } catch (error) {
      if (error instanceof PolicyError) {
        throw error;
      }
      logger.error('[PolicyReader] Read error:', error);
      throw new PolicyError(
        'Policy read failed',
        'READER_ERROR',
        error
      );
    }
  }
} 