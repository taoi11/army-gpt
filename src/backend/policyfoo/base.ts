import { config, ModelConfig } from '../config.js';
import { logger } from '../utils/logger.js';
import { llmProvider } from '../llm/provider.js';
import { LLMError } from '../utils/errors.js';
import type { CompletionOptions } from '../llm/provider.js';
import type { PolicyAgentOptions, Message } from './types.js';
import fs from 'fs/promises';
import path from 'path';

export abstract class BaseAgent {
  protected systemPrompt: string = '';
  protected readonly agentName: string;
  protected isInitialized = false;

  constructor(agentName: string) {
    this.agentName = agentName;
    this.loadSystemPrompt().catch(error => {
      logger.error(`Failed to load ${this.agentName} system prompt:`, error);
      throw error;
    });
  }

  /**
   * Load system prompt from file
   */
  protected async loadSystemPrompt(): Promise<void> {
    try {
      this.systemPrompt = await fs.readFile(
        path.join(config.paths.prompts, `${this.getPromptFileName()}.md`),
        'utf-8'
      );
      this.isInitialized = true;
      
      if (logger.isLevelEnabled('debug')) {
        logger.debug(`[${this.agentName}] System prompt loaded: ${this.systemPrompt.length} chars`);
      }
    } catch (error) {
      logger.error(`[${this.agentName}] Error loading system prompt:`, error);
      throw new LLMError(`Failed to load ${this.agentName} system prompt`);
    }
  }

  /**
   * Get the prompt file name for this agent
   */
  protected abstract getPromptFileName(): string;

  /**
   * Convert PolicyAgentOptions to LLM CompletionOptions
   */
  protected prepareLLMOptions(options: PolicyAgentOptions, isBackup: boolean): CompletionOptions {
    const baseConfig = this.getLLMConfig(isBackup);
    
    return {
      model: baseConfig.model,
      temperature: options.temperature ?? baseConfig.temperature,
      stream: options.stream ?? true,
      ...(isBackup ? {
        numCtx: baseConfig.numCtx,
        batchSize: baseConfig.batchSize
      } : {})
    };
  }

  /**
   * Get LLM config for this agent
   */
  protected abstract getLLMConfig(isBackup: boolean): ModelConfig['primary'] | ModelConfig['backup'];

  /**
   * Generate completion with proper error handling
   */
  protected async *generateCompletion(
    content: string,
    systemPrompt: string,
    messages?: Message[],
    options: PolicyAgentOptions = {},
    requestId?: string
  ): AsyncGenerator<string, void, unknown> {
    try {
      if (!this.isInitialized) {
        throw new LLMError(`${this.agentName} not initialized`);
      }

      if (!content.trim()) {
        throw new LLMError('Content cannot be empty');
      }

      // Debug logging
      if (logger.isLevelEnabled('debug')) {
        logger.debug(`[${this.agentName}] Processing request ${requestId?.slice(0, 8) || 'no-id'}`);
      }

      // Setup LLM options
      const primaryOptions = this.prepareLLMOptions(options, false);
      const backupOptions = this.prepareLLMOptions(options, true);

      // Generate completion
      yield* await llmProvider.generateCompletion(
        content,
        systemPrompt,
        messages,
        undefined,
        primaryOptions,
        backupOptions,
        requestId,
        this.agentName
      );

    } catch (error) {
      logger.error(`[${this.agentName}] Error generating completion:`, error);
      throw error instanceof LLMError ? error : new LLMError(`${this.agentName} generation failed`);
    }
  }

  /**
   * Generate completion synchronously
   */
  protected async generateSync(
    content: string,
    systemPrompt: string,
    messages?: Message[],
    options: PolicyAgentOptions = {},
    requestId?: string
  ): Promise<string> {
    const chunks: string[] = [];
    try {
      for await (const chunk of this.generateCompletion(
        content,
        systemPrompt,
        messages,
        { ...options, stream: false },
        requestId
      )) {
        chunks.push(chunk);
      }
      return chunks.join('');
    } catch (error) {
      logger.error(`[${this.agentName}] Error in synchronous generation:`, error);
      throw error instanceof LLMError ? error : new LLMError(`${this.agentName} sync generation failed`);
    }
  }
} 