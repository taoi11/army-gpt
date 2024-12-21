import winston from 'winston';
import { config } from '../config.js';

// Types
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

// Helper function to truncate long responses
export function truncateLLMResponse(response: any, headTailLength = 100): string {
  if (!response) {
    return String(response);
  }
  
  const responseStr = String(response);
  
  if (responseStr.length <= headTailLength * 2) {
    return responseStr;
  }
  
  const head = responseStr.slice(0, headTailLength);
  const tail = responseStr.slice(-headTailLength);
  const middleLength = responseStr.length - (headTailLength * 2);
  
  return `${head}... [${middleLength} chars truncated] ...${tail}`;
}

// Create logger instance
const loggerInstance = winston.createLogger({
  level: config.server.logLevel,
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
      const metaStr = Object.keys(meta).length ? JSON.stringify(meta) : '';
      return `${timestamp} - army-gpt - ${level}: ${message} ${metaStr}`;
    })
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});

// Add debug mode warning if enabled
if (config.server.debug) {
  loggerInstance.warn('Debug mode is enabled - verbose logging will be shown');
}

// Extend logger with isLevelEnabled method
interface ExtendedLogger extends winston.Logger {
  isLevelEnabled(level: LogLevel): boolean;
}

const logger = loggerInstance as ExtendedLogger;

// Add isLevelEnabled method
logger.isLevelEnabled = function(level: LogLevel): boolean {
  const currentLevel = this.level;
  const levels = this.levels;
  return levels[currentLevel] >= levels[level];
};

export { logger }; 