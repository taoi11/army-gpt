import { BaseAgent } from './base';
import { PolicyContent, PolicyError } from './types';
import { config } from '../config';
import { logger } from '../utils/logger';

export class PolicyReader extends BaseAgent {
  constructor() {
    super('PolicyReader');
  }

  protected getPromptFileName(): string {
    return 'policy-reader';
  }

  protected getLLMConfig(isBackup: boolean): any {
    return isBackup ? config.policy.reader.backup : config.policy.reader.primary;
  }

  async read(policyNumber: string, section: string, options: any = {}): Promise<PolicyContent> {
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