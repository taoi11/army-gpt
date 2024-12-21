import axios from 'axios';
import { config } from '../config';
import { logger, truncateLLMResponse } from '../utils/logger';
import { LLMError } from '../utils/errors';

// Types
interface Message {
  role: string;
  content: string;
}

interface CompletionOptions {
  model: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
  num_ctx?: number;
  batch_size?: number;
}

interface StreamChoice {
  delta: {
    content?: string;
  };
}

interface StreamResponse {
  id?: string;
  choices: StreamChoice[];
}

interface LLMRequestBody {
  messages: Message[];
  stream: boolean;
  temperature?: number;
  max_tokens?: number;
}

interface OllamaRequestBody extends LLMRequestBody {
  model: string;
  options?: {
    num_ctx?: number;
    batch_size?: number;
  };
}

export class LLMProvider {
  private primaryTimeout = { connect: 5000, read: 30000 }; // 5s connect, 30s read
  private backupTimeout = { connect: 5000, read: 90000 }; // 5s connect, 90s read

  constructor() {
    if (!config.llm.primary.apiKey) {
      throw new Error('OpenRouter API key not found in environment variables');
    }
  }

  private async *_primaryCompletion(
    prompt: string,
    systemPrompt: string,
    messages?: Message[],
    conversationHistory?: Message[],
    options?: CompletionOptions,
    requestId?: string,
    agentName?: string
  ): AsyncGenerator<string, void, unknown> {
    const model = options?.model;
    if (!model) {
      throw new Error('Model not specified in options');
    }

    // Use provided messages or format from conversation history
    const formattedMessages = messages || 
      this._prepareMessages(prompt, systemPrompt, messages, conversationHistory, agentName);

    const prefix = agentName ? `[${agentName}] ` : '';

    try {
      const requestBody: LLMRequestBody = {
        messages: formattedMessages,
        stream: true,
        temperature: options?.temperature,
        max_tokens: options?.max_tokens
      };

      const response = await axios.post(
        `${config.llm.primary.baseUrl}/chat/completions`,
        {
          ...requestBody,
          model
        },
        {
          headers: {
            'Authorization': `Bearer ${config.llm.primary.apiKey}`,
            'HTTP-Referer': 'https://github.com/taoi11/army-gpt',
            'X-Title': 'Army-GPT',
            'Content-Type': 'application/json'
          },
          timeout: this.primaryTimeout.read,
          responseType: 'stream'
        }
      );

      let generationId: string | undefined;

      for await (const chunk of response.data) {
        const lines = chunk.toString().split('\n');
        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;
          
          const data = line.slice(6); // Remove 'data: ' prefix
          if (data === '[DONE]') continue;

          try {
            const parsed: StreamResponse = JSON.parse(data);
            
            // Capture generation ID from first message
            if (!generationId && parsed.id) {
              generationId = parsed.id;
            }

            const content = parsed.choices[0]?.delta?.content;
            if (content) {
              yield content;
            }
          } catch (e) {
            logger.debug(`${prefix}Failed to parse JSON: ${data}`);
          }
        }
      }

      // Track cost after streaming is complete
      if (generationId) {
        await new Promise(resolve => setTimeout(resolve, 500));
        // TODO: Implement cost tracking
        // await costTracker.trackApiCall(generationId);
      }

    } catch (error: any) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        if (status === 402) {
          logger.error(`${prefix}OpenRouter credits exhausted`);
          throw new LLMError('OpenRouter credits exhausted');
        } else if (status === 429) {
          logger.error(`${prefix}OpenRouter rate limit exceeded`);
          throw new LLMError('OpenRouter rate limit exceeded');
        } else if (status === 500) {
          logger.error(`${prefix}OpenRouter server error: ${error.response?.data}`);
          throw new LLMError('OpenRouter server error');
        }
      }
      throw error;
    }
  }

  private async *_backupCompletion(
    prompt: string,
    systemPrompt: string,
    messages?: Message[],
    conversationHistory?: Message[],
    options?: CompletionOptions,
    requestId?: string,
    agentName?: string
  ): AsyncGenerator<string, void, unknown> {
    const model = options?.model;
    if (!model) {
      throw new Error('Model not specified in options');
    }

    const formattedMessages = messages || 
      this._prepareMessages(prompt, systemPrompt, messages, conversationHistory, agentName);

    const prefix = agentName ? `[${agentName}] ` : '';

    try {
      const requestBody: OllamaRequestBody = {
        model,
        messages: formattedMessages,
        stream: true,
        temperature: options?.temperature,
        options: {
          num_ctx: options?.num_ctx,
          batch_size: options?.batch_size
        }
      };

      const response = await axios.post(
        `${config.llm.backup.baseUrl}/api/generate`,
        requestBody,
        {
          timeout: this.backupTimeout.read,
          responseType: 'stream'
        }
      );

      for await (const chunk of response.data) {
        const lines = chunk.toString().split('\n');
        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const parsed = JSON.parse(line);
            if (parsed.response) {
              yield parsed.response;
            }
          } catch (e) {
            logger.debug(`${prefix}Failed to parse JSON: ${line}`);
          }
        }
      }

    } catch (error) {
      logger.error(`${prefix}Backup LLM error:`, error);
      throw new LLMError('Backup LLM error');
    }
  }

  private _prepareMessages(
    prompt: string,
    systemPrompt: string,
    messages?: Message[],
    conversationHistory?: Message[],
    agentName?: string
  ): Message[] {
    const formattedMessages: Message[] = [];
    const seenMessages = new Set<string>();

    // Add system prompt first if provided
    if (systemPrompt) {
      formattedMessages.push({ role: 'system', content: systemPrompt });
    }

    // Use provided messages if available, otherwise use conversation history
    if (messages) {
      // Skip system message if we already added one
      for (const msg of messages) {
        if (msg.role === 'system' && formattedMessages[0]?.role === 'system') {
          continue;
        }
        const msgKey = `${msg.role}:${msg.content.trim()}`;
        if (!seenMessages.has(msgKey)) {
          seenMessages.add(msgKey);
          formattedMessages.push(msg);
        }
      }
    } else if (conversationHistory) {
      // Add conversation history in chronological order
      for (const msg of conversationHistory) {
        const msgKey = `${msg.role}:${msg.content.trim()}`;
        if (!seenMessages.has(msgKey)) {
          seenMessages.add(msgKey);
          formattedMessages.push(msg);
        }
      }
    }

    // Add current user prompt if not already in history
    const currentPromptKey = `user:${prompt.trim()}`;
    if (!seenMessages.has(currentPromptKey)) {
      formattedMessages.push({ role: 'user', content: prompt });
    }

    // Only log message history in debug mode
    if (logger.isLevelEnabled('debug')) {
      const truncatedMessages = formattedMessages.map(msg => ({
        role: msg.role,
        content: truncateLLMResponse(msg.content)
      }));
      const prefix = agentName ? `[${agentName}] ` : '';
      logger.debug(`${prefix}Messages: ${JSON.stringify(truncatedMessages, null, 2)}`);
    }

    return formattedMessages;
  }

  async *generateCompletion(
    prompt: string,
    systemPrompt: string = '',
    messages?: Message[],
    conversationHistory?: Message[],
    primaryOptions?: CompletionOptions,
    backupOptions?: CompletionOptions,
    requestId?: string,
    agentName?: string
  ): AsyncGenerator<string, void, unknown> {
    try {
      // Format messages
      const formattedMessages = this._prepareMessages(
        prompt,
        systemPrompt,
        messages,
        conversationHistory,
        agentName
      );

      try {
        // Try primary LLM first
        yield* await this._primaryCompletion(
          prompt,
          systemPrompt,
          formattedMessages,
          undefined,
          primaryOptions,
          requestId,
          agentName
        );
      } catch (error) {
        logger.error('Primary LLM failed:', error);
        logger.debug('Falling back to backup LLM');

        // Fall back to backup LLM
        yield* await this._backupCompletion(
          prompt,
          systemPrompt,
          formattedMessages,
          undefined,
          backupOptions,
          requestId,
          agentName
        );
      }
    } catch (error) {
      logger.error('LLM completion failed:', error);
      logger.debug('Full error details:', error);
      throw error;
    }
  }
}

// Create singleton instance
export const llmProvider = new LLMProvider(); 