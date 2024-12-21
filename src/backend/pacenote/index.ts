import fs from 'fs/promises';
import path from 'path';
import { config } from '../config';
import { logger } from '../utils/logger';
import { llmProvider } from '../llm/provider';
import { LLMError } from '../utils/errors';
import type { CompletionOptions } from '../llm/provider';

// Types
interface PaceNoteOptions {
  temperature?: number;
  stream?: boolean;
  maxTokens?: number;
}

interface CompetencySection {
  competency: string;
  facets: string[];
}

class KnowledgeBaseError extends LLMError {
  constructor(
    message: string,
    public readonly type: 'SYSTEM_PROMPT_NOT_FOUND' | 'COMPETENCIES_NOT_FOUND' | 'EXAMPLES_NOT_FOUND' | 'PARSE_ERROR'
  ) {
    super(message);
    this.name = 'KnowledgeBaseError';
  }
}

export class PaceNoteAgent {
  private systemPrompt: string = '';
  private competencyList: string = '';
  private examples: string = '';
  private readonly AGENT_NAME = 'PaceNoteAgent';
  private isInitialized = false;

  constructor() {
    // Log initialization with models from config
    logger.debug(`${this.AGENT_NAME} initialized with models:`, {
      primary: config.paceNote.primary.model,
      backup: config.paceNote.backup.model
    });

    // Load knowledge base
    this.loadKnowledgeBase().then(() => {
      this.isInitialized = true;
      logger.info(`${this.AGENT_NAME} knowledge base loaded successfully`);
    }).catch((error: Error) => {
      logger.error('Failed to load PaceNoteAgent knowledge base:', error);
      throw error;
    });
  }

  /**
   * Parse competencies from markdown table format
   */
  private parseCompetencies(content: string): string {
    if (!content.trim()) {
      throw new KnowledgeBaseError('Empty competencies content', 'PARSE_ERROR');
    }

    const competencies: CompetencySection[] = [];
    let currentSection: CompetencySection | null = null;

    // Split content into lines and process each line
    const lines = content.split('\n');
    for (const line of lines) {
      // Skip header and separator lines
      if (!line.includes('|') || line.includes('---')) {
        continue;
      }

      // Parse table row
      const parts = line.split('|').map(p => p.trim()).filter(Boolean);
      if (parts.length < 2) continue;

      const [competency, facet] = [parts[0], parts[1]];

      // If we have a competency, start a new section
      if (competency) {
        if (currentSection) {
          competencies.push(currentSection);
        }
        currentSection = { competency, facets: [] };
      }

      // Add facet to current section
      if (currentSection && facet) {
        currentSection.facets.push(facet);
      }
    }

    // Add the last section
    if (currentSection) {
      competencies.push(currentSection);
    }

    if (competencies.length === 0) {
      throw new KnowledgeBaseError('No competencies found in content', 'PARSE_ERROR');
    }

    // Format competencies into string
    return competencies
      .map(section => {
        const facetsStr = section.facets
          .map(facet => `    - ${facet}`)
          .join('\n');
        return `- ${section.competency}:\n${facetsStr}`;
      })
      .join('\n');
  }

  /**
   * Load and prepare knowledge base files
   */
  private async loadKnowledgeBase(): Promise<void> {
    try {
      // Load system prompt
      try {
        this.systemPrompt = await fs.readFile(
          path.join(config.paths.prompts, 'pace-note.md'),
          'utf-8'
        );
      } catch (error) {
        throw new KnowledgeBaseError(
          'Failed to load system prompt: ' + (error as Error).message,
          'SYSTEM_PROMPT_NOT_FOUND'
        );
      }

      // Load and parse competencies
      try {
        const competenciesContent = await fs.readFile(
          path.join(config.paths.policies, 'pace-note', 'competency.md'),
          'utf-8'
        );
        this.competencyList = this.parseCompetencies(competenciesContent);
      } catch (error) {
        if (error instanceof KnowledgeBaseError) throw error;
        throw new KnowledgeBaseError(
          'Failed to load competencies: ' + (error as Error).message,
          'COMPETENCIES_NOT_FOUND'
        );
      }

      // Load examples
      try {
        this.examples = await fs.readFile(
          path.join(config.paths.policies, 'pace-note', 'example_notes.md'),
          'utf-8'
        );
      } catch (error) {
        throw new KnowledgeBaseError(
          'Failed to load examples: ' + (error as Error).message,
          'EXAMPLES_NOT_FOUND'
        );
      }

      // Debug logging
      if (logger.isLevelEnabled('debug')) {
        logger.debug(`[${this.AGENT_NAME}] System prompt loaded: ${this.systemPrompt.length} chars`);
        logger.debug(`[${this.AGENT_NAME}] Competency list loaded: ${this.competencyList.length} chars`);
        logger.debug(`[${this.AGENT_NAME}] Examples loaded: ${this.examples.length} chars`);
      }

    } catch (error) {
      logger.error(`[${this.AGENT_NAME}] Error loading knowledge base:`, error);
      throw error instanceof KnowledgeBaseError ? error : new LLMError('Failed to load knowledge base');
    }
  }

  /**
   * Prepare the full prompt with competencies and examples
   */
  private preparePrompt(content: string): string {
    if (!this.isInitialized) {
      throw new LLMError('PaceNoteAgent not initialized');
    }

    return this.systemPrompt
      .replace('{{competency_list}}', this.competencyList)
      .replace('{{examples}}', this.examples)
      + '\n\nMember Details:\n' + content;
  }

  /**
   * Convert PaceNoteOptions to LLM CompletionOptions
   */
  private prepareLLMOptions(options: PaceNoteOptions, isBackup: boolean): CompletionOptions {
    const baseConfig = isBackup ? config.paceNote.backup : config.paceNote.primary;
    
    return {
      model: baseConfig.model,
      temperature: options.temperature ?? baseConfig.temperature,
      maxTokens: options.maxTokens ?? (isBackup ? undefined : baseConfig.maxTokens),
      stream: options.stream ?? true,
      ...(isBackup ? {
        numCtx: config.paceNote.backup.numCtx,
        batchSize: config.paceNote.backup.batchSize
      } : {})
    };
  }

  /**
   * Generate pace notes with streaming support
   */
  async *generate(
    content: string,
    options: PaceNoteOptions = {},
    requestId?: string
  ): AsyncGenerator<string, void, unknown> {
    try {
      if (!content.trim()) {
        throw new LLMError('Content cannot be empty');
      }

      // Debug logging
      if (logger.isLevelEnabled('debug')) {
        logger.debug(`[${this.AGENT_NAME}] Processing request ${requestId?.slice(0, 8) || 'no-id'}`);
      }

      // Prepare the prompt
      const prompt = this.preparePrompt(content);

      // Setup LLM options
      const primaryOptions = this.prepareLLMOptions(options, false);
      const backupOptions = this.prepareLLMOptions(options, true);

      // Generate completion
      yield* await llmProvider.generateCompletion(
        content,
        prompt,
        undefined,
        undefined,
        primaryOptions,
        backupOptions,
        requestId,
        this.AGENT_NAME
      );

    } catch (error) {
      logger.error(`[${this.AGENT_NAME}] Error generating pace note:`, error);
      throw error instanceof LLMError ? error : new LLMError('Failed to generate pace note');
    }
  }

  /**
   * Generate pace notes synchronously (non-streaming)
   */
  async generateSync(
    content: string,
    options: PaceNoteOptions = {},
    requestId?: string
  ): Promise<string> {
    const chunks: string[] = [];
    try {
      for await (const chunk of this.generate(content, { ...options, stream: false }, requestId)) {
        chunks.push(chunk);
      }
      return chunks.join('');
    } catch (error) {
      logger.error(`[${this.AGENT_NAME}] Error in synchronous generation:`, error);
      throw error instanceof LLMError ? error : new LLMError('Failed to generate pace note');
    }
  }
}

// Create singleton instance
export const paceNoteAgent = new PaceNoteAgent(); 