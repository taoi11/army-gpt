import { BaseAgent } from './base.js';
import { Message, PolicyResponse, PolicyError, PolicyAgentOptions, formatResponse, parseResponse } from './types.js';
import { config, ModelConfig } from '../config.js';
import { logger } from '../utils/logger.js';

export class PolicyChat extends BaseAgent {
  constructor() {
    super('PolicyChat');
  }

  protected getPromptFileName(): string {
    return 'chatAgent';
  }

  protected getLLMConfig(isBackup: boolean): ModelConfig['primary'] | ModelConfig['backup'] {
    return isBackup ? config.policy.chat.backup : config.policy.chat.primary;
  }

  async respond(message: string, history: Message[] = [], options: PolicyAgentOptions = {}): Promise<PolicyResponse> {
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

  async *streamResponse(message: string, history: Message[] = [], options: PolicyAgentOptions = {}): AsyncGenerator<string, void, unknown> {
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