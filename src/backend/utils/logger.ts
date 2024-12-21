import winston from 'winston';
import { config } from '../config';

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
  level: config.debug ? 'debug' : 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ timestamp, level, message }) => {
      return `${timestamp} - army-gpt - ${level}: ${message}`;
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
if (config.debug) {
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