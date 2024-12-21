import { FastifyRequest, FastifyReply } from 'fastify';
import { logger } from './logger';

// Custom error types
export class AppError extends Error {
  constructor(
    message: string,
    public statusCode: number = 500,
    public code: string = 'INTERNAL_SERVER_ERROR'
  ) {
    super(message);
    this.name = this.constructor.name;
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = 'Rate limit exceeded') {
    super(message, 429, 'RATE_LIMIT_EXCEEDED');
  }
}

export class LLMError extends AppError {
  constructor(message: string = 'LLM service error') {
    super(message, 503, 'LLM_SERVICE_ERROR');
  }
}

// Global error handler
export async function errorHandler(
  error: Error,
  request: FastifyRequest,
  reply: FastifyReply
) {
  // Log the error
  logger.error(`Global error handler caught: ${error.message}`);
  
  // Handle known errors
  if (error instanceof AppError) {
    return reply.status(error.statusCode).send({
      code: error.code,
      message: error.message
    });
  }

  // Handle unknown errors
  return reply.status(500).send({
    code: 'INTERNAL_SERVER_ERROR',
    message: 'Internal server error'
  });
} 