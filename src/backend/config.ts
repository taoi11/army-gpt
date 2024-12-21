import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config();

// Types
type LogLevel = 'debug' | 'info' | 'warn' | 'error';
type ModelProvider = 'OpenRouter' | 'Ollama';

export interface ServerConfig {
  port: number;
  host: string;
  debug: boolean;
  jwtSecret: string;
  logLevel: LogLevel;
}

export interface RateLimitConfig {
  hourlyLimit: number;
  dailyLimit: number;
  enabled: boolean;
}

export interface LLMConfig {
  primary: {
    baseUrl: string;
    apiKey: string;
    creditCheckInterval: number;
    provider: ModelProvider;
  };
  backup: {
    baseUrl: string;
    provider: ModelProvider;
  };
}

export interface ModelConfig {
  primary: {
    model: string;
    temperature?: number;
  };
  backup: {
    model: string;
    numCtx: number;
    batchSize: number;
    temperature?: number;
  };
}

export interface PathConfig {
  static: string;
  templates: string;
  data: string;
  policies: string;
  prompts: string;
}

export interface Config {
  server: ServerConfig;
  rateLimiting: RateLimitConfig;
  llm: LLMConfig;
  paceNote: ModelConfig;
  policy: {
    finder: ModelConfig;
    reader: ModelConfig;
    chat: ModelConfig;
  };
  paths: PathConfig;
}

// Configuration object
export const config: Config = {
  server: {
    port: parseInt(process.env.PORT || '8020', 10),
    host: process.env.HOST || '0.0.0.0',
    debug: process.env.DEBUG_MODE === 'true',
    jwtSecret: process.env.JWT_SECRET || 'default-secret-key',
    logLevel: (process.env.LOG_LEVEL || 'info') as LogLevel
  },

  rateLimiting: {
    hourlyLimit: parseInt(process.env.RATE_LIMIT_PER_HOUR || '20', 10),
    dailyLimit: parseInt(process.env.RATE_LIMIT_PER_DAY || '50', 10),
    enabled: true
  },

  llm: {
    primary: {
      baseUrl: process.env.LLM_BASE_URL || 'https://openrouter.ai/api/v1',
      apiKey: process.env.OPENROUTER_API_KEY || '',
      creditCheckInterval: 5 * 60 * 1000, // 5 minutes
      provider: 'OpenRouter'
    },
    backup: {
      baseUrl: process.env.BACKUP_LLM_BASE_URL || 'http://localhost:11434',
      provider: 'Ollama'
    }
  },

  paceNote: {
    primary: {
      model: process.env.PACE_NOTE_MODEL || 'amazon/nova-pro-v1',
      temperature: 0.1
    },
    backup: {
      model: process.env.BACKUP_PACE_NOTE_MODEL || 'qwen2.5:32b-instruct-q4_K_S',
      numCtx: parseInt(process.env.BACKUP_PACE_NOTE_NUM_CTX || '14336', 10),
      batchSize: parseInt(process.env.BACKUP_PACE_NOTE_BATCH_SIZE || '256', 10),
      temperature: 0.1
    }
  },

  policy: {
    finder: {
      primary: {
        model: process.env.POLICY_FINDER_MODEL || 'google/gemini-flash-1.5',
        temperature: 0.1
      },
      backup: {
        model: process.env.BACKUP_POLICY_FINDER_MODEL || 'llama3.2:3b-instruct-q8_0',
        numCtx: parseInt(process.env.BACKUP_POLICY_FINDER_NUM_CTX || '81920', 10),
        batchSize: parseInt(process.env.BACKUP_POLICY_FINDER_BATCH_SIZE || '1024', 10),
        temperature: 0.1
      }
    },
    reader: {
      primary: {
        model: process.env.POLICY_READER_MODEL || 'amazon/nova-lite-v1',
        temperature: 0.1
      },
      backup: {
        model: process.env.BACKUP_POLICY_READER_MODEL || 'llama3.2:3b-instruct-q8_0',
        numCtx: parseInt(process.env.BACKUP_POLICY_READER_NUM_CTX || '81920', 10),
        batchSize: parseInt(process.env.BACKUP_POLICY_READER_BATCH_SIZE || '1024', 10),
        temperature: 0.1
      }
    },
    chat: {
      primary: {
        model: process.env.CHAT_AGENT_MODEL || 'amazon/nova-pro-v1',
        temperature: 0.1
      },
      backup: {
        model: process.env.BACKUP_CHAT_AGENT_MODEL || 'qwen2.5:32b-instruct-q4_K_S',
        numCtx: parseInt(process.env.BACKUP_CHAT_AGENT_NUM_CTX || '20480', 10),
        batchSize: parseInt(process.env.BACKUP_CHAT_AGENT_BATCH_SIZE || '32', 10),
        temperature: 0.1
      }
    }
  },

  paths: {
    static: path.join(__dirname, '../../frontend/static'),
    templates: path.join(__dirname, '../../frontend/templates'),
    data: path.join(__dirname, '../../data'),
    policies: path.join(__dirname, '../../policies'),
    prompts: path.join(__dirname, '../prompts')
  }
}; 