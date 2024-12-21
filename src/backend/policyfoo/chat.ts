import { BaseAgent } from './base';
import { Message, PolicyResponse, PolicyError, formatResponse, parseResponse } from './types';
import { config } from '../config';
import { logger } from '../utils/logger';

export class PolicyChat extends BaseAgent {
  constructor() {
    super('PolicyChat');
  }

  protected getPromptFileName(): string {
    return 'policy-chat';
  }

  protected getLLMConfig(isBackup: boolean): any {
    return isBackup ? config.policy.chat.backup : config.policy.chat.primary;
  }

  async respond(message: string, history: Message[] = [], options: any = {}): Promise<PolicyResponse> {
    try {
      const response = await this.generateSync(
        message,
        this.systemPrompt,
        history,
        options
      );

      // Parse response and validate
      try {
        return parseResponse(response);
      } catch (e) {
        logger.error('[PolicyChat] Failed to parse response:', e);
        throw new PolicyError(
          'Failed to parse chat response',
          'CHAT_ERROR',
          e
        );
      }
    } catch (error) {
      if (error instanceof PolicyError) {
        throw error;
      }
      logger.error('[PolicyChat] Response error:', error);
      throw new PolicyError(
        'Chat response failed',
        'CHAT_ERROR',
        error
      );
    }
  }

  async *streamResponse(message: string, history: Message[] = [], options: any = {}): AsyncGenerator<string, void, unknown> {
    try {
      yield* this.generateCompletion(
        message,
        this.systemPrompt,
        history,
        { ...options, stream: true }
      );
    } catch (error) {
      logger.error('[PolicyChat] Stream error:', error);
      throw error instanceof PolicyError ? error : new PolicyError(
        'Chat stream failed',
        'CHAT_ERROR',
        error
      );
    }
  }
} 